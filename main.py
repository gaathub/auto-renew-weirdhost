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

def run_cloud_fix():
    print("🚀 [云端] 启动自动续费 (大屏修正版)...")
    with sync_playwright() as p:
        # 1. 启动浏览器 (Headless模式)
        browser = p.chromium.launch(headless=True)
        
        # 🔥 修正点 A: 强制设置 1920x1080 分辨率
        # 这样网页就不会变成手机版，按钮一定会在原来的位置
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
            
            # --- 登录流程 ---
            if "login" in page.url:
                print("2. 点击 Discord 登录...")
                if page.locator("input[type='checkbox']").count() > 0:
                    page.locator("input[type='checkbox']").check(force=True)
                
                try:
                    page.click("text=디스코드로 로그인하기", timeout=5000)
                except:
                    page.click("a[href*='discord']", timeout=5000)

                print("3. 处理 Discord 登录...")
                page.wait_for_load_state("networkidle")

                # 处理 APP 弹窗 (云端有时候也会遇到)
                if page.locator("button:has-text('继续使用')").count() > 0:
                    page.locator("button:has-text('继续使用')").click()

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
            
            print("4. 等待登录跳转...")
            try:
                page.wait_for_url(lambda url: "weirdhost.xyz" in url and "login" not in url, timeout=60000)
            except:
                print("   -> 跳转超时，强制进入主页")
                page.goto(HOME_URL)

            # --- 🔥 修正点 B: 模拟人工导航 (不再直接跳转 URL) ---
            print("5. 开始导航到服务器...")
            # 确保在主页
            if page.url != HOME_URL:
                page.goto(HOME_URL)
                page.wait_for_load_state("networkidle")

            # 点击 "服务器" (Servers)
            print("   -> 点击 '서버' 标签...")
            page.locator("span:text-is('서버'), div:has-text('서버')").first.click()
            page.wait_for_timeout(2000)

            # 点击 "Discord's Bot Server"
            print("   -> 点击目标服务器...")
            page.locator("a[href*='/server/10a4aaad']").first.click()
            page.wait_for_load_state("networkidle")

            # --- 续费流程 ---
            print("6. 点击续费...")
            # 🔥 修正点 C: 增加等待时间到 30秒
            renew_btn = page.locator("span:has-text('시간추가')").first
            renew_btn.wait_for(state="visible", timeout=30000) 
            renew_btn.scroll_into_view_if_needed()
            renew_btn.click()
            
            # 检查结果
            try:
                # 检查是否有红色错误提示
                error_msg = page.locator("text=You can't renew")
                error_msg.wait_for(state="visible", timeout=5000)
                print("❌ 结果：还没到续费时间 (操作已执行)")
            except:
                print("✅ 结果：续费成功 (未检测到错误)")

        except Exception as e:
            print(f"❌ 运行出错: {e}")
            # 截图会保存在 Artifacts 中
            page.screenshot(path="error_screenshot.png")
            raise e 

        finally:
            browser.close()

if __name__ == "__main__":
    run_cloud_fix()
