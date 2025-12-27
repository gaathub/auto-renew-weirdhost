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

def run_cloud_debug():
    print("🚀 [云端调试模式] 启动...")
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
            print("1. [调试] 准备访问登录页...")
            page.goto(LOGIN_URL, timeout=60000)
            print(f"   -> 当前 URL: {page.url}")
            
            # --- 登录流程 ---
            if "login" in page.url:
                print("2. [调试] 开始登录流程...")
                # 勾选条款
                if page.locator("input[type='checkbox']").count() > 0:
                    page.locator("input[type='checkbox']").check(force=True)
                    print("   -> 条款已勾选")
                
                # 点击按钮
                print("   -> 点击 Discord 按钮...")
                try:
                    page.click("text=디스코드로 로그인하기", timeout=5000)
                except:
                    print("   -> 文本定位失败，尝试链接定位...")
                    page.click("a[href*='discord']", timeout=5000)

                print("3. [调试] 等待 Discord 页面加载...")
                page.wait_for_load_state("networkidle")
                print(f"   -> 当前 URL: {page.url}")

                # 处理 APP 弹窗
                if page.locator("button:has-text('继续使用')").count() > 0:
                    print("   -> 关闭 APP 弹窗")
                    page.locator("button:has-text('继续使用')").click()

                # 填写账号
                if page.locator("input[name='email']").is_visible():
                    print("   -> 输入账号密码")
                    page.fill("input[name='email']", DISCORD_EMAIL)
                    page.fill("input[name='password']", DISCORD_PASSWORD)
                    page.click("button[type='submit']")
                    page.wait_for_timeout(3000)

                # 2FA
                if page.locator("input[autocomplete='one-time-code']").count() > 0:
                    print("   -> 输入 2FA")
                    totp = pyotp.TOTP(TWO_FA_SECRET)
                    page.fill("input[autocomplete='one-time-code']", totp.now())
                    page.click("button[type='submit']")
                    page.wait_for_timeout(3000)

                # 授权
                auth_btn = page.locator("button:has-text('Authorize'), button:has-text('授权'), button:has-text('승인')").last
                if auth_btn.count() > 0:
                    print("   -> 点击授权")
                    auth_btn.click()
            
            print("4. [调试] 等待登录跳转回主页...")
            try:
                page.wait_for_url(lambda url: "weirdhost.xyz" in url and "login" not in url, timeout=60000)
                print(f"   -> 跳转成功，当前 URL: {page.url}")
            except:
                print("   -> 跳转超时，尝试强制进入主页")
                page.goto(HOME_URL)

            # --- 导航流程 ---
            print("5. [调试] 开始导航到服务器页...")
            if page.url != HOME_URL:
                page.goto(HOME_URL)
                page.wait_for_load_state("networkidle")

            print("   -> 点击 '서버'...")
            page.locator("span:text-is('서버'), div:has-text('서버')").first.click()
            
            print("   -> 点击目标服务器...")
            # 这里增加一个等待，确保目标服务器按钮出现
            target_server = page.locator("a[href*='/server/10a4aaad']").first
            target_server.wait_for(state="visible", timeout=10000)
            target_server.click()
            page.wait_for_load_state("networkidle")
            print(f"   -> 已进入服务器页，当前 URL: {page.url}")

            # --- 续费流程 ---
            print("6. [调试] 寻找续费按钮...")
            renew_btn = page.locator("span:has-text('시간추가')").first
            # 关键：这里是最容易报错的地方，等待 30 秒，并确保滚动到可见
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
                print("✅ [结果] 续费成功 (未检测到错误)")

        except Exception as e:
            print(f"\n❌❌❌ 运行出错! 正在截图...")
            print(f"错误信息: {e}")
            # 🔥🔥🔥 关键：报错时截图 🔥🔥🔥
            page.screenshot(path="error_screenshot.png", full_page=True)
            print("📸 已保存全屏截图: error_screenshot.png")
            # 再次抛出异常，让 Action 显示红色失败
            raise e 

        finally:
            browser.close()

if __name__ == "__main__":
    run_cloud_debug()
