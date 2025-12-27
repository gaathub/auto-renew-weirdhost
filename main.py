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

def run_cloud_fixed():
    print("🚀 [云端修复版] 启动...")
    with sync_playwright() as p:
        # --- 🔥 核心修复：云端必须是 headless=True ---
        # 只有在本地电脑测试时才能用 False
        browser = p.chromium.launch(
            headless=True, 
            args=["--disable-blink-features=AutomationControlled"] # 反检测参数
        )
        
        # 伪装成普通 Windows 浏览器的 User-Agent
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        # 拦截 Discord APP 唤起
        page.route("**/*", lambda route: route.abort() if "discord://" in route.request.url else route.continue_())

        try:
            # 1. 访问登录页
            print("1️⃣ 访问登录页...")
            page.goto(LOGIN_URL, timeout=60000)
            
            # 判断是否需要登录
            if "login" in page.url:
                print("   -> 正在登录...")
                
                # [A] 勾选条款
                try:
                    checkbox = page.locator("input[type='checkbox']")
                    if checkbox.count() > 0 and not checkbox.is_checked():
                        checkbox.check(force=True)
                        time.sleep(0.5)
                except:
                    pass

                # [B] 点击 Discord
                print("   -> 点击 Discord 按钮...")
                discord_btn = page.locator("a[href*='discord']").first
                if not discord_btn.is_visible():
                    discord_btn = page.locator("text=디스코드로 로그인하기").first
                
                discord_btn.click()
                
                # 等待跳转
                try:
                    page.wait_for_url(lambda url: "discord.com" in url, timeout=30000)
                    print("   -> 已跳转 Discord")
                except:
                    print("   ❌ 跳转 Discord 失败")
                    raise Exception("Discord Jump Failed")

                # [C] Discord 验证
                page.wait_for_load_state("domcontentloaded")
                time.sleep(2)
                
                # 截图：看看是不是有人机验证
                page.screenshot(path="01_discord_check.png") 

                # 填账号
                if page.locator("input[name='email']").is_visible():
                    print("   -> 输入账号密码...")
                    page.fill("input[name='email']", DISCORD_EMAIL)
                    page.fill("input[name='password']", DISCORD_PASSWORD)
                    page.click("button[type='submit']")
                    time.sleep(3)
                
                # 检查是否出现 hCaptcha (云端最容易挂在这里)
                if page.locator("iframe[src*='hcaptcha']").count() > 0:
                    print("❌❌❌ 遭遇 hCaptcha 验证码！云端无法通过！")
                    print("建议：在本地运行提取 storage_state.json 上传到云端。")
                    page.screenshot(path="captcha_block.png")
                    raise Exception("Blocked by Captcha")

                # 2FA
                if page.locator("input[autocomplete='one-time-code']").count() > 0:
                    print("   -> 输入 2FA...")
                    totp = pyotp.TOTP(TWO_FA_SECRET)
                    page.fill("input[autocomplete='one-time-code']", totp.now())
                    page.click("button[type='submit']")
                    time.sleep(3)

                # 授权
                try:
                    auth_btn = page.locator("button:has-text('Authorize'), button:has-text('授权'), button:has-text('승인')").last
                    auth_btn.wait_for(state="visible", timeout=5000)
                    auth_btn.click()
                    print("   -> 点击授权")
                except:
                    pass

                # 等待跳回
                print("⏳ 等待回调...")
                try:
                    page.wait_for_url(lambda url: "weirdhost.xyz" in url and "discord" not in url, timeout=60000)
                except:
                    print("   ❌ 回调超时")
                    page.screenshot(path="callback_fail.png")
                    raise Exception("Callback Timeout")

            # 2. 续费
            print("2️⃣ 前往服务器页...")
            page.goto(TARGET_SERVER_URL)
            page.wait_for_load_state("domcontentloaded")

            if "login" in page.url:
                print("❌❌❌ 登录失败 (Session Lost)")
                page.screenshot(path="session_lost.png")
                raise Exception("Login Failed")

            print("3️⃣ 点击续费...")
            try:
                renew_btn = page.locator("span:has-text('시간추가')").first
                renew_btn.wait_for(state="visible", timeout=20000)
                renew_btn.scroll_into_view_if_needed()
                renew_btn.click()
                print("   ✅ 按钮已点击")
                
                try:
                    page.locator("text=You can't renew").wait_for(state="visible", timeout=5000)
                    print("   ❌ 还没到时间")
                except:
                    print("   ✅ 续费成功")

            except Exception as e:
                print(f"   ❌ 没找到按钮: {e}")
                page.screenshot(path="no_button.png")
                raise e

        except Exception as e:
            print(f"💥 运行错误: {e}")
            page.screenshot(path="crash.png")
            raise e

        finally:
            browser.close()

if __name__ == "__main__":
    run_cloud_fixed()
