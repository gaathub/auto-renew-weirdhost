import os
import time
import pyotp
from playwright.sync_api import sync_playwright

# --- 环境变量获取 ---
DISCORD_EMAIL = os.environ["DIS_EMAIL"]
DISCORD_PASSWORD = os.environ["DIS_PASSWORD"]
TWO_FA_SECRET = os.environ["DIS_SECRET"].replace(" ", "")

LOGIN_URL = "https://hub.weirdhost.xyz/auth/login"
# 直接定义目标服务器地址，跳过中间点击步骤
TARGET_SERVER_URL = "https://hub.weirdhost.xyz/server/10a4aaad"
HOME_URL = "https://hub.weirdhost.xyz/"

def run_cloud_fast():
    print("🚀 [极速直达版] 启动自动续费...")
    with sync_playwright() as p:
        # 启动浏览器
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
            # 改为 domcontentloaded，不等动态资源
            page.wait_for_load_state("domcontentloaded") 
            
            # --- 登录流程 ---
            if "login" in page.url:
                print("2. 开始登录流程...")
                
                # 勾选条款
                try:
                    checkbox = page.locator("input[type='checkbox']")
                    if checkbox.count() > 0:
                        checkbox.check(force=True)
                except:
                    pass

                # 点击 Discord 按钮 (混合策略)
                print("   -> 点击 Discord 登录按钮...")
                try:
                    # 优先找链接
                    page.click("a[href*='discord']", timeout=5000)
                except:
                    try:
                        # 其次找按钮文字
                        page.click("text=Discord", timeout=5000)
                    except:
                        # 最后盲点最后一个按钮
                        buttons = page.locator("button, .btn, div[role='button']")
                        if buttons.count() > 0:
                            buttons.last.click(force=True)

                print("3. 等待 Discord 页面...")
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
                    page.wait_for_timeout(2000)

                # 2FA
                if page.locator("input[autocomplete='one-time-code']").count() > 0:
                    print("   -> 输入 2FA...")
                    totp = pyotp.TOTP(TWO_FA_SECRET)
                    page.fill("input[autocomplete='one-time-code']", totp.now())
                    page.click("button[type='submit']")
                    page.wait_for_timeout(2000)

                # 授权
                auth_btn = page.locator("button:has-text('Authorize'), button:has-text('授权'), button:has-text('승인')").last
                if auth_btn.count() > 0:
                    print("   -> 点击授权...")
                    auth_btn.click()
            
            # --- 关键修改：直接跳转到服务器页面 ---
            print("4. 等待登录完成...")
            # 只要 URL 变了或者离开了登录页就算成功，不等完全加载
            try:
                page.wait_for_url(lambda url: "login" not in url, timeout=30000)
            except:
                print("   -> 等待跳转超时，尝试强制直连...")

            print(f"5. 🚀 直飞目标服务器: {TARGET_SERVER_URL}")
            page.goto(TARGET_SERVER_URL)
            # 只等待 DOM 结构加载完成，不再等 networkidle
            page.wait_for_load_state("domcontentloaded")

            # --- 续费流程 ---
            print("6. 寻找续费按钮...")
            try:
                # 寻找包含“시간추가”的 span 元素
                renew_btn = page.locator("span").filter(has_text="시간추가").first
                
                # 等待它出现 (最多30秒)
                renew_btn.wait_for(state="visible", timeout=30000) 
                
                # 滚动到可见区域并点击
                renew_btn.scroll_into_view_if_needed()
                print("   -> 点击续费按钮...")
                renew_btn.click()
                
                # 检查结果
                try:
                    # 检测红色错误提示
                    error_msg = page.locator("text=You can't renew")
                    error_msg.wait_for(state="visible", timeout=5000)
                    print("❌ [结果] 还没到续费时间")
                except:
                    print("✅ [结果] 续费成功")
                    
            except Exception as e:
                # 如果找不到按钮，可能是页面还在加载数据，截图看看
                print(f"❌ 找不到续费按钮 (可能页面动态数据未加载完): {e}")
                raise e

        except Exception as e:
            print(f"❌ 运行出错: {e}")
            page.screenshot(path="error_screenshot.png", full_page=True)
            raise e 

        finally:
            browser.close()

if __name__ == "__main__":
    run_cloud_fast()
