import os
import time
import pyotp
from playwright.sync_api import sync_playwright

# --- 🔴 配置区域 ---
# 为了安全，建议去 GitHub Settings -> Secrets 里配置。
# 如果你非要写在代码里，请直接替换下面的 os.environ[...]
DISCORD_EMAIL = os.environ.get("DIS_EMAIL", "cbdyyk@outlook.com")
DISCORD_PASSWORD = os.environ.get("DIS_PASSWORD", "YOUR_PASSWORD_HERE") # <--- 如果不通过环境变量，请在这里填入密码
TWO_FA_SECRET = os.environ.get("DIS_SECRET", "f7he xstx 43co tvlc lwmd nad7 vp4i ibya").replace(" ", "")

# 网址
LOGIN_URL = "https://hub.weirdhost.xyz/auth/login"
TARGET_SERVER_URL = "https://hub.weirdhost.xyz/server/10a4aaad"

def run_final_fix():
    print("🚀 [死磕填表版] 启动...")
    with sync_playwright() as p:
        # 云端必须 headless=True
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
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
            
            # 如果在登录页，开始操作
            if "login" in page.url:
                print("   -> 正在处理前置操作...")
                
                # [A] 勾选条款 (循环多次确保勾上)
                for i in range(3):
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
                
                # 死等跳转
                print("   -> 等待跳转至 Discord...")
                try:
                    page.wait_for_url(lambda url: "discord.com" in url, timeout=30000)
                    print("   -> ✅ 已抵达 Discord 页面")
                except:
                    print("   ❌ 跳转失败")
                    raise Exception("Jump Failed")

                # ==========================================
                # 🔥 核心修正：必须等待输入框出现 🔥
                # ==========================================
                print("2️⃣ Discord 身份验证...")
                page.wait_for_load_state("domcontentloaded")
                
                # 这里的逻辑改成了：必须等到输入框出现，否则报错，绝不跳过！
                print("   -> 正在寻找账号输入框 (死等模式)...")
                try:
                    email_input = page.locator("input[name='email']")
                    # 最长等 25 秒
                    email_input.wait_for(state="visible", timeout=25000)
                    
                    print("   -> ✅ 找到输入框，开始填写...")
                    email_input.fill(DISCORD_EMAIL)
                    page.locator("input[name='password']").fill(DISCORD_PASSWORD)
                    
                    # 提交前截图
                    page.screenshot(path="01_before_submit.png")
                    
                    page.locator("button[type='submit']").click()
                    print("   -> 账号密码已提交！")
                    
                    # 提交后等待一下
                    time.sleep(5)
                    page.screenshot(path="02_after_submit.png")
                    
                except Exception as e:
                    print(f"   ❌ 错误：找不到输入框！当前页面截图已保存。")
                    page.screenshot(path="debug_no_input.png")
                    # 如果找不到输入框，有可能是已经自动登录了，尝试继续检查
                    if "discord" in page.url:
                         print("   ⚠️ 仍在 Discord 页面但找不到输入框，可能遇到了验证码或加载失败。")
                         raise e

                # --- 2FA 处理 ---
                print("   -> 检查 2FA...")
                try:
                    otp_input = page.locator("input[autocomplete='one-time-code']")
                    # 给它 5 秒钟出现时间
                    if otp_input.count() > 0 or otp_input.is_visible():
                        print("   -> 🔐 检测到 2FA 请求，正在输入...")
                        totp = pyotp.TOTP(TWO_FA_SECRET)
                        code = totp.now()
                        otp_input.fill(code)
                        page.locator("button[type='submit']").click()
                        print("   -> 2FA 已提交")
                        time.sleep(3)
                except:
                    pass

                # --- 授权按钮 ---
                print("   -> 检查授权按钮...")
                try:
                    auth_btn = page.locator("button:has-text('Authorize'), button:has-text('授权'), button:has-text('승인')").last
                    # 等待按钮可见
                    auth_btn.wait_for(state="visible", timeout=10000)
                    auth_btn.click()
                    print("   -> ✅ 点击授权")
                except:
                    print("   -> 未发现授权按钮 (可能已自动通过)")

                # 等待回调
                print("⏳ 等待跳转回 WeirdHost...")
                try:
                    page.wait_for_url(lambda url: "weirdhost.xyz" in url and "discord" not in url, timeout=60000)
                    print("   -> ✅ 回调成功")
                except:
                    print("   ❌ 回调超时 (可能卡在 Discord 页面)")
                    page.screenshot(path="callback_timeout.png")
                    raise Exception("Callback Timeout")

            # 3. 续费
            print("3️⃣ 前往服务器页...")
            page.goto(TARGET_SERVER_URL)
            page.wait_for_load_state("domcontentloaded")

            if "login" in page.url:
                print("❌❌❌ 登录失败 (Session Lost)")
                page.screenshot(path="session_lost.png")
                raise Exception("Login Failed")

            print("4️⃣ 点击续费...")
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
    run_final_fix()
