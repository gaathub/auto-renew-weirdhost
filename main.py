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

def run_blocking_wait():
    print("🚀 [死等响应版] 启动...")
    with sync_playwright() as p:
        # 启动浏览器 (Headless模式)
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
            print("1️⃣ 访问 WeirdHost 登录页...")
            page.goto(LOGIN_URL)
            page.wait_for_load_state("networkidle")

            # 检查是否就在登录页
            if "login" in page.url:
                print("   -> 正在处理登录前置操作...")

                # [A] 勾选条款 (必须确保勾上)
                try:
                    checkbox = page.locator("input[type='checkbox']")
                    checkbox.wait_for(state="visible", timeout=10000)
                    if not checkbox.is_checked():
                        checkbox.check(force=True)
                        time.sleep(1) # 等1秒让JS生效
                except:
                    print("   ⚠️ 勾选条款时遇到小问题，尝试继续...")

                # [B] 点击 Discord 登录 (并等待跳转)
                print("   -> 点击 Discord 按钮，等待跳转...")
                
                # 寻找按钮
                discord_btn = page.locator("a[href*='discord']").first
                if not discord_btn.is_visible():
                    discord_btn = page.locator("text=디스코드로 로그인하기").first
                
                # 点击并等待 URL 变成 discord.com
                discord_btn.click()
                
                try:
                    # 🔥 核心修改：死等 URL 变化，最长等 30秒
                    page.wait_for_url(lambda url: "discord.com" in url, timeout=30000)
                    print("   -> ✅ 已成功跳转到 Discord 域名")
                except:
                    print("   ❌ 跳转 Discord 超时！可能是按钮没点到，或者网络太慢。")
                    raise Exception("Failed to reach Discord")

                # --- 2. Discord 登录流程 (一步一步死等) ---
                print("2️⃣ 开始 Discord 身份验证...")
                page.wait_for_load_state("domcontentloaded")

                # [C] 填写账号 (死等输入框出现)
                print("   -> 正在寻找账号输入框...")
                try:
                    email_input = page.locator("input[name='email']")
                    # 🔥 核心修改：这里必须等，直到输入框出现在屏幕上
                    email_input.wait_for(state="visible", timeout=20000)
                    
                    print("   -> 输入框已出现，正在填写...")
                    email_input.fill(DISCORD_EMAIL)
                    page.fill("input[name='password']", DISCORD_PASSWORD)
                    page.click("button[type='submit']")
                    print("   -> 账号密码已提交")
                except Exception as e:
                    print(f"   ⚠️ 没有找到账号输入框 (可能已经记住登录了?): {e}")

                # [D] 填写 2FA (如果有)
                try:
                    # 等待一下看会不会出现 2FA 框
                    otp_input = page.locator("input[autocomplete='one-time-code']")
                    # 给它 5 秒钟出现时间
                    otp_input.wait_for(state="visible", timeout=5000)
                    
                    print("   -> 检测到 2FA 请求，正在计算验证码...")
                    totp = pyotp.TOTP(TWO_FA_SECRET)
                    otp_input.fill(totp.now())
                    page.click("button[type='submit']")
                    print("   -> 2FA 验证码已提交")
                except:
                    print("   -> 未检测到 2FA (或已通过)")

                # [E] 点击授权 (Authorize) - 最容易卡的一步
                print("   -> 正在等待 '授权' 按钮...")
                try:
                    # 查找授权按钮
                    auth_btn = page.locator("button:has-text('Authorize'), button:has-text('授权'), button:has-text('승인')").last
                    # 🔥 核心修改：死等授权按钮出现，最长 15秒
                    auth_btn.wait_for(state="visible", timeout=15000)
                    # 再次等待 2 秒确保按钮可点击
                    time.sleep(2)
                    auth_btn.click()
                    print("   -> ✅ 已点击 '授权' 按钮")
                except:
                    print("   ⚠️ 未找到授权按钮 (可能已自动授权)，继续...")

                # --- 3. 等待跳回 ---
                print("3️⃣ 等待跳转回 WeirdHost 控制台...")
                try:
                    # 死等 URL 变回 weirdhost
                    page.wait_for_url(lambda url: "weirdhost.xyz" in url and "discord" not in url, timeout=40000)
                    print("   -> 回调成功！")
                except:
                    print("   ❌ 跳转回控制台超时！")
                    page.screenshot(path="callback_timeout.png")
                    raise Exception("Callback Timeout")

            # --- 4. 验证登录并续费 ---
            # 此时应该在首页，再次确认不在 login 页面
            if "login" in page.url:
                print("❌❌❌ 依然在登录页！登录流程失败。")
                page.screenshot(path="login_failed.png")
                raise Exception("Login Failed Final")

            print(f"4️⃣ 前往服务器页面: {TARGET_SERVER_URL}")
            page.goto(TARGET_SERVER_URL)
            # 等待服务器页面加载
            page.wait_for_load_state("domcontentloaded")
            
            # 再次检查 Session
            if "login" in page.url:
                print("❌❌❌ Session 丢失，无法访问服务器页。")
                raise Exception("Session Lost")

            print("5️⃣ 寻找续费按钮...")
            try:
                # 寻找按钮
                renew_btn = page.locator("span").filter(has_text="시간추가").first
                # 死等按钮出现
                renew_btn.wait_for(state="visible", timeout=20000)
                renew_btn.scroll_into_view_if_needed()
                renew_btn.click()
                print("   -> ✅ 按钮已点击")

                # 6. 检查结果
                try:
                    error_msg = page.locator("text=You can't renew")
                    error_msg.wait_for(state="visible", timeout=5000)
                    print("❌ [结果] 还没到续费时间")
                except:
                    print("✅ [结果] 续费成功")

            except Exception as e:
                print(f"❌ 找不到续费按钮: {e}")
                # 截图方便排查
                page.screenshot(path="no_button.png")
                raise e

        except Exception as e:
            print(f"💥 运行异常: {e}")
            page.screenshot(path="crash_report.png")
            raise e

        finally:
            browser.close()

if __name__ == "__main__":
    run_blocking_wait()
