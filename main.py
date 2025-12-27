import os
import time
import pyotp
from playwright.sync_api import sync_playwright

# --- 环境变量 ---
DISCORD_EMAIL = os.environ["DIS_EMAIL"]
DISCORD_PASSWORD = os.environ["DIS_PASSWORD"]
TWO_FA_SECRET = os.environ["DIS_SECRET"].replace(" ", "")

LOGIN_URL = "https://hub.weirdhost.xyz/auth/login"
TARGET_SERVER_URL = "https://hub.weirdhost.xyz/server/10a4aaad"

def run_debug_visual():
    print("🚀 [全程监控版] 启动...")
    with sync_playwright() as p:
        # 启动浏览器 (1920x1080)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 拦截 Discord APP 唤起
        page.route("**/*", lambda route: route.abort() if "discord://" in route.request.url else route.continue_())

        try:
            # --- 1. 访问登录页 ---
            print("📸 [1] 正在访问登录页...")
            page.goto(LOGIN_URL, timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            page.screenshot(path="01_login_page.png") # 截图1: 初始页面
            
            if "login" in page.url:
                print("   -> 检测到登录页，开始登录流程")
                
                # 勾选条款
                try:
                    page.locator("input[type='checkbox']").check(force=True)
                except:
                    pass

                # 点击 Discord 按钮
                print("   -> 点击 Discord 按钮...")
                try:
                    page.click("a[href*='discord']", timeout=5000)
                except:
                    # 备用点击
                    buttons = page.locator("button, .btn, div[role='button']")
                    if buttons.count() > 0:
                        buttons.last.click(force=True)
                
                # --- 2. Discord 页面 ---
                print("📸 [2] 等待 Discord 加载...")
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3) # 稍微等一下让页面渲染
                page.screenshot(path="02_discord_page.png") # 截图2: Discord 页面长啥样
                
                # 处理 APP 弹窗
                if page.locator("button:has-text('继续使用')").count() > 0:
                    page.locator("button:has-text('继续使用')").click()

                # 填写账号
                if page.locator("input[name='email']").is_visible():
                    print("   -> 填写账号密码...")
                    page.fill("input[name='email']", DISCORD_EMAIL)
                    page.fill("input[name='password']", DISCORD_PASSWORD)
                    page.click("button[type='submit']")
                    time.sleep(3)

                # 2FA
                if page.locator("input[autocomplete='one-time-code']").count() > 0:
                    print("   -> 填写 2FA...")
                    totp = pyotp.TOTP(TWO_FA_SECRET)
                    page.fill("input[autocomplete='one-time-code']", totp.now())
                    page.click("button[type='submit']")
                    time.sleep(3)

                # 授权
                auth_btn = page.locator("button:has-text('Authorize'), button:has-text('授权'), button:has-text('승인')").last
                if auth_btn.count() > 0:
                    print("   -> 点击授权...")
                    auth_btn.click()
                    time.sleep(5)
            
            # --- 3. 登录后状态检查 ---
            print("📸 [3] 登录操作结束，检查当前状态...")
            page.wait_for_load_state("domcontentloaded")
            page.screenshot(path="03_after_login.png") # 截图3: 登录完是什么页面？
            
            print(f"   -> 当前 URL: {page.url}")

            # --- 4. 强制前往服务器 ---
            print(f"🚀 [4] 前往服务器页面: {TARGET_SERVER_URL}")
            page.goto(TARGET_SERVER_URL)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(5) # 给它5秒加载时间
            
            print("📸 [5] 到达服务器页，截图留念...")
            page.screenshot(path="04_server_page.png") # 截图4: 服务器页面到底加载出来没？

            # --- 5. 寻找续费按钮 ---
            print("🔍 [6] 寻找续费按钮...")
            try:
                # 寻找 span
                renew_btn = page.locator("span").filter(has_text="시간추가").first
                if renew_btn.is_visible():
                    renew_btn.click()
                    print("✅ 按钮点击成功！")
                    page.screenshot(path="05_success.png")
                else:
                    print("⚠️ 按钮未直接显示，尝试滚动...")
                    renew_btn.scroll_into_view_if_needed()
                    renew_btn.click(timeout=5000)
                    print("✅ 滚动后点击成功！")
            except Exception as e:
                print(f"❌ 找不到按钮: {e}")
                # 如果没找到，这里不用抛出异常，因为我们已经有截图 04_server_page.png 了
                # 只要程序不报错退出，后面的 run.yml 就能把截图传上去
                
        except Exception as e:
            print(f"❌ 发生严重错误: {e}")
            page.screenshot(path="99_crash_error.png")
            raise e

        finally:
            browser.close()

if __name__ == "__main__":
    run_debug_visual()
