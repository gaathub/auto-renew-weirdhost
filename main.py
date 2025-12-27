import os
import time
import pyotp
from playwright.sync_api import sync_playwright

# --- 从环境变量获取密码 (为了安全) ---
DISCORD_EMAIL = os.environ["DIS_EMAIL"]
DISCORD_PASSWORD = os.environ["DIS_PASSWORD"]
TWO_FA_SECRET = os.environ["DIS_SECRET"].replace(" ", "")

LOGIN_URL = "https://hub.weirdhost.xyz/auth/login"
HOME_URL = "https://hub.weirdhost.xyz/"

def run_cloud():
    print("🚀 [云端] 启动自动续费...")
    with sync_playwright() as p:
        # ⚠️ 云端必须用 headless=True (无界面模式)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 拦截 Discord APP 唤起
        page.route("**/*", lambda route: route.abort() if "discord://" in route.request.url else route.continue_())

        try:
            print("1. 访问登录页...")
            page.goto(LOGIN_URL, timeout=60000)
            
            # --- 登录流程 ---
            print("2. 点击 Discord 登录...")
            # 勾选条款
            if page.locator("input[type='checkbox']").count() > 0:
                page.locator("input[type='checkbox']").check(force=True)
            
            # 点击按钮
            try:
                page.click("text=디스코드로 로그인하기", timeout=5000)
            except:
                page.click("a[href*='discord']", timeout=5000)

            print("3. 处理 Discord 登录...")
            page.wait_for_load_state("networkidle")

            # 填写账号
            if page.locator("input[name='email']").is_visible():
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
            
            # 等待跳转
            print("4. 等待跳转回面板...")
            page.wait_for_url(lambda url: "weirdhost.xyz" in url and "login" not in url, timeout=60000)

            # --- 续费流程 ---
            print("5. 前往服务器页面...")
            page.goto("https://hub.weirdhost.xyz/server/10a4aaad")
            page.wait_for_load_state("networkidle")

            print("6. 点击续费...")
            renew_btn = page.locator("span:has-text('시간추가')").first
            renew_btn.wait_for(state="visible", timeout=10000)
            renew_btn.click()
            
            # 检查结果
            try:
                page.locator("text=You can't renew").wait_for(state="visible", timeout=5000)
                print("❌ 还没到续费时间")
            except:
                print("✅ 续费成功 (未检测到错误)")

        except Exception as e:
            print(f"❌ 运行出错: {e}")
            # 截图保存 (GitHub Actions 可以在 Artifacts 里下载看到)
            page.screenshot(path="error.png")
            raise e # 抛出异常让 Action 显示红色失败

        finally:
            browser.close()

if __name__ == "__main__":
    run_cloud()
