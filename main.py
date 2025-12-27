import os
import time
import pyotp
from playwright.sync_api import sync_playwright

# --- 环境变量获取 ---
DISCORD_EMAIL = os.environ["DIS_EMAIL"]
DISCORD_PASSWORD = os.environ["DIS_PASSWORD"]
TWO_FA_SECRET = os.environ["DIS_SECRET"].replace(" ", "")

LOGIN_URL = "https://hub.weirdhost.xyz/auth/login"
HOME_URL = "https://hub.weirdhost.xyz/"

def run_cloud_force():
    print("🚀 [暴力点击版] 启动自动续费...")
    with sync_playwright() as p:
        # 启动浏览器 (Headless模式, 1920x1080大屏)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 拦截 Discord APP 唤起
        page.route("**/*", lambda route: route.abort() if "discord://" in route.request.url else route.continue_())

        try:
            print("1. 访问登录页...")
            page.goto(LOGIN_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # --- 登录流程 ---
            if "login" in page.url:
                print("2. 开始登录流程...")
                
                # 勾选条款
                try:
                    checkbox = page.locator("input[type='checkbox']")
                    if checkbox.count() > 0:
                        checkbox.check(force=True)
                        print("   -> 条款已勾选")
                except:
                    pass

                # 🔥🔥🔥 暴力点击 Discord 按钮逻辑 🔥🔥🔥
                print("   -> 尝试点击 Discord 按钮...")
                clicked = False
                
                # 方案A: 找链接 (通常最稳)
                if not clicked:
                    try:
                        print("   -> [尝试A] 寻找 href 包含 discord 的链接...")
                        btn = page.locator("a[href*='discord']").first
                        if btn.is_visible():
                            btn.click(timeout=3000)
                            clicked = True
                            print("   -> 成功点击链接！")
                    except:
                        pass
                
                # 方案B: 找韩文关键字 (模糊匹配)
                if not clicked:
                    try:
                        print("   -> [尝试B] 寻找包含 '디스코드' 的元素...")
                        # 只要包含这几个字就点
                        page.get_by_text("디스코드", exact=False).last.click(timeout=3000)
                        clicked = True
                        print("   -> 成功点击韩文文本！")
                    except:
                        pass
                
                # 方案C: 找 'Discord' 英文
                if not clicked:
                    try:
                        print("   -> [尝试C] 寻找 'Discord' 英文...")
                        page.get_by_text("Discord", exact=False).last.click(timeout=3000)
                        clicked = True
                    except:
                        pass
                
                # 方案D: 盲点最后一个按钮 (终极方案)
                if not clicked:
                    print("   -> [尝试D] 点击页面上最后一个按钮...")
                    try:
                        # 既然是登录页，最后一个大按钮通常就是第三方登录
                        buttons = page.locator("button, .btn, div[role='button']")
                        count = buttons.count()
                        if count > 0:
                            buttons.nth(count - 1).click(force=True)
                            print("   -> 已点击最后一个按钮")
                        else:
                            print("   -> 😱 没找到任何按钮！")
                    except:
                        pass

                # --- 后续流程 ---
                print("3. 等待 Discord 页面加载...")
                try:
                    # 等待 URL 变化
                    page.wait_for_url(lambda url: "discord" in url or "weirdhost" in url, timeout=15000)
                except:
                    print("   ⚠️ 警告: URL 未变化，可能点击失败或已登录")

                page.wait_for_load_state("domcontentloaded")

                # 处理 APP 弹窗
                if page.locator("button:has-text('继续使用')").count() > 0:
                    page.locator("button:has-text('继续使用')").click()

                # 填写账号
                if page.locator("input[name='email']").is_visible():
                    print("   -> 输入账号密码...")
                    page.fill("input[name='email']", DISCORD_EMAIL)
                    page.fill("input[name='password']", DISCORD_PASSWORD)
                    page.click("button[type='submit']")
                    page.wait_for_timeout(3000)

                # 2FA
                if page.locator("input[autocomplete='one-time-code']").count() > 0:
                    print("   -> 输入 2FA...")
                    totp = pyotp.TOTP(TWO_FA_SECRET)
                    page.fill("input[autocomplete='one-time-code']", totp.now())
                    page.click("button[type='submit']")
                    page.wait_for_timeout(3000)

                # 授权
                auth_btn = page.locator("button:has-text('Authorize'), button:has-text('授权'), button:has-text('승인')").last
                if auth_btn.count() > 0:
                    print("   -> 点击授权...")
                    auth_btn.click()
            
            print("4. 等待跳转回主页...")
            try:
                page.wait_for_url(lambda url: "weirdhost.xyz" in url and "login" not in url, timeout=60000)
            except:
                print("   -> 跳转超时，强制进入主页")
                page.goto(HOME_URL)

            # --- 导航流程 ---
            print("5. 导航到服务器页...")
            if page.url != HOME_URL:
                page.goto(HOME_URL)
                page.wait_for_load_state("networkidle")

            # 点击 '서버'
            print("   -> 点击服务器标签...")
            try:
                page.locator("span:text-is('서버'), div:has-text('서버')").first.click()
            except:
                page.goto(HOME_URL + "/server/10a4aaad") # 备用直连

            # 点击目标服务器
            print("   -> 点击目标服务器...")
            try:
                target_server = page.locator("a[href*='/server/10a4aaad']").first
                target_server.wait_for(state="visible", timeout=10000)
                target_server.click()
            except:
                pass
            
            page.wait_for_load_state("networkidle")

            # --- 续费流程 ---
            print("6. 寻找续费按钮...")
            # 同样使用包含匹配，更稳
            try:
                renew_btn = page.locator("span").filter(has_text="시간추가").first
                renew_btn.wait_for(state="visible", timeout=30000) 
                renew_btn.scroll_into_view_if_needed()
                print("   -> 点击续费按钮...")
                renew_btn.click()
                
                # 检查结果
                try:
                    error_msg = page.locator("text=You can't renew")
                    error_msg.wait_for(state="visible", timeout=5000)
                    print("❌ [结果] 还没到续费时间")
                except:
                    print("✅ [结果] 续费成功")
            except Exception as e:
                print(f"❌ 找不到续费按钮: {e}")
                # 如果没找到按钮，可能已经在服务器页了，再试一次直连
                if "server" in page.url:
                     print("   -> 尝试备用方案...")

        except Exception as e:
            print(f"❌ 运行出错: {e}")
            page.screenshot(path="error_screenshot.png", full_page=True)
            raise e 

        finally:
            browser.close()

if __name__ == "__main__":
    run_cloud_force()
