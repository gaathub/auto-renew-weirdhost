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

def run_force_fill():
    print("🚀 [强制填表版] 启动...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        # 拦截 Discord APP 唤起，防止卡死
        page.route("**/*", lambda route: route.abort() if "discord://" in route.request.url else route.continue_())

        try:
            # ==========================
            # 1. WeirdHost 登录页操作
            # ==========================
            print("1️⃣ 访问登录页...")
            page.goto(LOGIN_URL, timeout=60000)
            page.wait_for_load_state("domcontentloaded")

            if "login" in page.url:
                print("   -> [A] 正在处理条款...")
                # 循环确保勾选
                for i in range(5):
                    checkbox = page.locator("input[type='checkbox']")
                    if checkbox.count() > 0:
                        if not checkbox.is_checked():
                            checkbox.check(force=True)
                            time.sleep(0.5)
                        else:
                            break
                
                print("   -> [B] 点击 Discord 登录...")
                # 寻找按钮
                discord_btn = page.locator("a[href*='discord']").first
                if not discord_btn.is_visible():
                    discord_btn = page.locator("text=디스코드로 로그인하기").first
                
                # 点击并等待跳转
                discord_btn.click()
                try:
                    # 死等 URL 变成 discord
                    page.wait_for_url(lambda url: "discord.com" in url, timeout=30000)
                    print("   -> ✅ 成功抵达 Discord！")
                except:
                    print("   ❌ 跳转 Discord 失败，可能按钮没点到")
                    raise Exception("Discord Jump Failed")

                # ==========================
                # 2. Discord 登录流程 (关键)
                # ==========================
                print("2️⃣ Discord 身份验证...")
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3) # 等待页面渲染
                
                # 📸 关键截图：看看 Discord 页面到底长啥样
                page.screenshot(path="01_discord_landing.png")
                print("   -> 已保存截图: 01_discord_landing.png")

                # 检查是否需要登录 (死等输入框)
                print("   -> 正在寻找邮箱输入框...")
                try:
                    # 这里的 wait_for 是关键，必须等它出来，不能跳过
                    page.locator("input[name='email']").wait_for(state="visible", timeout=15000)
                    
                    print("   -> 输入框出现，开始填写...")
                    page.locator("input[name='email']").fill(DISCORD_EMAIL)
                    page.locator("input[name='password']").fill(DISCORD_PASSWORD)
                    page.locator("button[type='submit']").click()
                    print("   -> 账号密码已提交")
                    time.sleep(3)
                except:
                    print("   ⚠️ 未找到邮箱输入框，可能已经由于缓存自动登录了？")

                # 检查 2FA
                if page.locator("input[autocomplete='one-time-code']").count() > 0:
                    print("   -> 检测到 2FA，正在输入...")
                    totp = pyotp.TOTP(TWO_FA_SECRET)
                    page.locator("input[autocomplete='one-time-code']").fill(totp.now())
                    page.locator("button[type='submit']").click()
                    time.sleep(3)

                # 📸 关键截图：登录点完之后长啥样
                page.screenshot(path="02_discord_after_login.png")

                # 检查授权按钮 (Authorize)
                print("   -> 检查授权按钮...")
                try:
                    auth_btn = page.locator("button:has-text('Authorize'), button:has-text('授权'), button:has-text('승인')").last
                    # 等待一下看按钮会不会出来
                    auth_btn.wait_for(state="visible", timeout=5000)
                    auth_btn.click()
                    print("   -> ✅ 点击了授权按钮")
                except:
                    print("   -> 未发现授权按钮 (可能已自动跳过)")

                # ==========================
                # 3. 回调与验证
                # ==========================
                print("3️⃣ 等待跳转回控制台...")
                try:
                    # 死等 URL 变回 weirdhost
                    page.wait_for_url(lambda url: "weirdhost.xyz" in url and "discord" not in url, timeout=60000)
                    print("   -> ✅ 回调成功")
                except:
                    print("   ❌ 回调超时！")
                    page.screenshot(path="callback_stuck.png")
                    raise Exception("Callback Failed")

            # ==========================
            # 4. 续费操作
            # ==========================
            print("4️⃣ 验证登录状态...")
            page.wait_for_load_state("domcontentloaded")
            
            # 如果还在 login 页面，说明刚才没登进去
            if "login" in page.url:
                print("❌❌❌ 登录失败！依然停留在登录页。请检查 01_discord_landing.png")
                page.screenshot(path="login_failed_final.png")
                raise Exception("Login Failed")

            print(f"   -> 前往服务器页: {TARGET_SERVER_URL}")
            page.goto(TARGET_SERVER_URL)
            page.wait_for_load_state("domcontentloaded")
            
            # 再次检查 Session
            if "login" in page.url:
                print("❌❌❌ Session 丢失！可能是 Discord 登录没成功。")
                page.screenshot(path="session_lost.png")
                raise Exception("Session Lost")

            print("5️⃣ 点击续费...")
            try:
                renew_btn = page.locator("span").filter(has_text="시간추가").first
                renew_btn.wait_for(state="visible", timeout=20000)
                renew_btn.scroll_into_view_if_needed()
                renew_btn.click()
                print("✅ 按钮已点击")
                
                try:
                    page.locator("text=You can't renew").wait_for(state="visible", timeout=5000)
                    print("❌ 结果：还没到时间")
                except:
                    print("✅ 结果：续费可能成功")

            except Exception as e:
                print(f"❌ 找不到续费按钮: {e}")
                page.screenshot(path="no_button.png")
                raise e

        except Exception as e:
            print(f"💥 运行崩溃: {e}")
            page.screenshot(path="crash.png")
            raise e

        finally:
            browser.close()

if __name__ == "__main__":
    run_force_fill()
