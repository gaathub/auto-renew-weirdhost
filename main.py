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

def run_retry_mode():
    print("🚀 [无脑重试版] 启动...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.route("**/*", lambda route: route.abort() if "discord://" in route.request.url else route.continue_())

        try:
            # --- 1. 访问登录页 (增加超时时间) ---
            print("1️⃣ 访问登录页 (超时设为60秒)...")
            try:
                # 就算网络卡，只要能加载出一部分就行，所以用 domcontentloaded
                page.goto(LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
            except:
                print("   ⚠️ 页面加载超时，尝试直接操作...")

            # 确保真的在登录页
            if "login" in page.url:
                print("   -> 正在处理登录...")

                # --- [A] 死磕条款 (循环检查) ---
                print("   -> [A] 正在勾选条款...")
                try:
                    checkbox = page.locator("input[type='checkbox']")
                    checkbox.wait_for(state="attached", timeout=10000)
                    
                    # 循环尝试勾选 5 次，直到真的勾上
                    for i in range(5):
                        if not checkbox.is_checked():
                            print(f"      第 {i+1} 次尝试勾选...")
                            checkbox.check(force=True)
                            time.sleep(1)
                        else:
                            print("      ✅ 条款已确认勾选")
                            break
                except:
                    print("   ⚠️ 条款勾选可能失败，尝试 JS 强制点击...")
                    page.evaluate("document.querySelector('input[type=checkbox]').click()")

                # --- [B] 死磕跳转 (循环点击) ---
                print("   -> [B] 点击 Discord 登录...")
                
                # 寻找按钮
                discord_btn = page.locator("a[href*='discord']").first
                if not discord_btn.is_visible():
                    discord_btn = page.locator("text=디스코드로 로그인하기").first
                
                # 循环点击直到 URL 变化
                max_retries = 3
                jumped = False
                for i in range(max_retries):
                    print(f"      第 {i+1} 次点击按钮...")
                    try:
                        discord_btn.click(timeout=3000)
                        # 等待 5 秒看 URL 变没变
                        try:
                            page.wait_for_url(lambda url: "discord.com" in url, timeout=5000)
                            jumped = True
                            print("      ✅ 成功跳转到 Discord！")
                            break
                        except:
                            print("      ⚠️ URL 未变化，重试...")
                    except:
                        pass
                
                if not jumped:
                    print("   ❌ 多次点击无效，最后尝试备用按钮...")
                    page.locator("button, .btn").last.click(force=True)
                    page.wait_for_url(lambda url: "discord.com" in url, timeout=10000)

                # --- 2. Discord 流程 ---
                print("2️⃣ Discord 验证...")
                page.wait_for_load_state("domcontentloaded")
                
                # 填账号 (死等出现)
                if page.locator("input[name='email']").count() > 0 or page.locator("input[name='password']").count() > 0:
                    print("   -> 输入账号密码...")
                    page.locator("input[name='email']").fill(DISCORD_EMAIL)
                    page.locator("input[name='password']").fill(DISCORD_PASSWORD)
                    page.locator("button[type='submit']").click()
                    page.wait_for_timeout(3000)

                # 填 2FA
                if page.locator("input[autocomplete='one-time-code']").count() > 0:
                    print("   -> 输入 2FA...")
                    totp = pyotp.TOTP(TWO_FA_SECRET)
                    page.locator("input[autocomplete='one-time-code']").fill(totp.now())
                    page.locator("button[type='submit']").click()
                    page.wait_for_timeout(3000)

                # 授权
                print("   -> 检查授权...")
                try:
                    auth_btn = page.locator("button:has-text('Authorize'), button:has-text('授权'), button:has-text('승인')").last
                    if auth_btn.is_visible():
                        auth_btn.click()
                        print("   -> ✅ 点击授权")
                        # 点击后必须死等跳回
                        page.wait_for_url(lambda url: "weirdhost.xyz" in url, timeout=60000)
                    else:
                        print("   -> 无授权按钮，自动跳过")
                except:
                    pass

            # --- 3. 验证与续费 ---
            print("3️⃣ 检查结果并续费...")
            page.wait_for_load_state("domcontentloaded")
            
            if "login" in page.url:
                print("❌❌❌ 失败：依然在登录页！")
                page.screenshot(path="failed_login.png")
                raise Exception("Login Loop Failed")

            print(f"   -> 前往: {TARGET_SERVER_URL}")
            page.goto(TARGET_SERVER_URL)
            page.wait_for_load_state("domcontentloaded")

            if "login" in page.url:
                print("❌❌❌ 失败：Session 丢失！")
                raise Exception("Session Lost")

            # 找按钮
            try:
                renew_btn = page.locator("span").filter(has_text="시간추가").first
                renew_btn.wait_for(state="visible", timeout=20000)
                renew_btn.scroll_into_view_if_needed()
                renew_btn.click()
                print("✅ 按钮已点击！")
                
                # 检查结果
                try:
                    page.locator("text=You can't renew").wait_for(state="visible", timeout=5000)
                    print("❌ 结果：还没到时间")
                except:
                    print("✅ 结果：续费成功")

            except Exception as e:
                print(f"❌ 找不到续费按钮: {e}")
                page.screenshot(path="no_btn.png")
                raise e

        except Exception as e:
            print(f"💥 运行崩溃: {e}")
            page.screenshot(path="crash.png")
            raise e

        finally:
            browser.close()

if __name__ == "__main__":
    run_retry_mode()
