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

def run_stable_login():
    print("🚀 [稳健等待版] 启动...")
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
            print("1️⃣ 访问登录页...")
            page.goto(LOGIN_URL)
            # 等待网页骨架加载完
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2) # 再多等2秒让脚本缓一缓

            if "login" in page.url:
                print("   -> 检测到登录界面...")

                # --- 步骤 A: 勾选条款 ---
                print("   -> [A] 勾选条款...")
                try:
                    # 等待复选框出现
                    checkbox = page.locator("input[type='checkbox']")
                    checkbox.wait_for(state="visible", timeout=10000)
                    
                    # 强制勾选
                    if not checkbox.is_checked():
                        checkbox.check(force=True)
                        print("      已执行勾选")
                    else:
                        print("      条款看似已勾选")
                    
                    # 🔥 关键：勾选后强制等待 2 秒，防止按钮还没变绿就点击
                    time.sleep(2) 
                    
                except Exception as e:
                    print(f"   ⚠️ 条款操作警告: {e}")

                # --- 步骤 B: 点击 Discord 登录 ---
                print("   -> [B] 点击 Discord 登录按钮...")
                
                # 寻找按钮 (优先找链接，其次找文字)
                discord_btn = page.locator("a[href*='discord']").first
                if not discord_btn.is_visible():
                    discord_btn = page.locator("text=디스코드로 로그인하기").first
                
                # 点击按钮
                discord_btn.click()
                print("      按钮已点击，等待跳转到 Discord...")

                # 🔥 关键修改：不再用 expect_navigation，而是死等 URL 包含 'discord.com'
                try:
                    page.wait_for_url(lambda url: "discord.com" in url or "weirdhost" in url, timeout=30000)
                    print("   -> ✅ 跳转成功！")
                except:
                    print("   ❌ 跳转超时！可能是点击没生效，尝试备用点击方案...")
                    # 备用：盲点最后一个按钮
                    page.locator("button, .btn").last.click(force=True)
                    page.wait_for_url(lambda url: "discord.com" in url, timeout=15000)

                # --- 步骤 C: Discord 流程 ---
                # 再次确认是否真的在 Discord 页面
                page.wait_for_load_state("domcontentloaded")
                
                if "discord.com" in page.url:
                    print("2️⃣ Discord 验证流程...")
                    time.sleep(2) # 等页面元素渲染

                    # 1. 关掉 APP 弹窗
                    if page.locator("button:has-text('继续使用')").count() > 0:
                        page.locator("button:has-text('继续使用')").click()
                        time.sleep(1)

                    # 2. 填账号
                    if page.locator("input[name='email']").is_visible():
                        print("   -> 输入账号...")
                        page.fill("input[name='email']", DISCORD_EMAIL)
                        page.fill("input[name='password']", DISCORD_PASSWORD)
                        page.click("button[type='submit']")
                        # 等待转圈
                        try:
                            page.wait_for_selector("input[autocomplete='one-time-code']", timeout=5000)
                        except:
                            time.sleep(3) 

                    # 3. 填 2FA
                    if page.locator("input[autocomplete='one-time-code']").count() > 0:
                        print("   -> 输入 2FA...")
                        totp = pyotp.TOTP(TWO_FA_SECRET)
                        page.fill("input[autocomplete='one-time-code']", totp.now())
                        page.click("button[type='submit']")
                        time.sleep(3)

                    # 4. 授权
                    print("   -> 检查授权按钮...")
                    try:
                        # 等待授权按钮出现
                        auth_btn = page.locator("button:has-text('Authorize'), button:has-text('授权'), button:has-text('승인')").last
                        # 只有按钮可见才点
                        if auth_btn.is_visible():
                            auth_btn.click()
                            print("   -> ✅ 已点击授权")
                            # 点击后死等跳转回 WeirdHost
                            page.wait_for_url(lambda url: "weirdhost.xyz" in url, timeout=30000)
                        else:
                            print("   -> 未发现授权按钮，可能已自动通过")
                    except:
                        pass

            # --- 步骤 D: 检查是否登录成功 ---
            print("3️⃣ 检查登录状态...")
            page.wait_for_load_state("domcontentloaded")
            
            # 如果 URL 里还有 login，说明失败了
            if "login" in page.url:
                print("❌❌❌ 依然在登录页，登录失败！")
                page.screenshot(path="login_failed_final.png")
                raise Exception("Login Failed")

            # --- 步骤 E: 续费 ---
            print(f"4️⃣ 前往服务器页面: {TARGET_SERVER_URL}")
            page.goto(TARGET_SERVER_URL)
            page.wait_for_load_state("domcontentloaded")
            
            if "login" in page.url:
                print("❌❌❌ Session 丢失，被弹回登录页")
                page.screenshot(path="session_lost.png")
                raise Exception("Session Lost")

            print("5️⃣ 点击续费...")
            try:
                # 寻找按钮
                renew_btn = page.locator("span").filter(has_text="시간추가").first
                renew_btn.wait_for(state="visible", timeout=20000)
                renew_btn.scroll_into_view_if_needed()
                renew_btn.click()
                print("   -> 按钮已点击")

                # 检查结果 (等待错误提示或成功)
                try:
                    error_msg = page.locator("text=You can't renew")
                    error_msg.wait_for(state="visible", timeout=5000)
                    print("❌ [结果] 还没到续费时间")
                except:
                    print("✅ [结果] 续费成功")

            except Exception as e:
                print(f"❌ 找不到续费按钮: {e}")
                page.screenshot(path="no_button.png")
                raise e

        except Exception as e:
            print(f"💥 运行异常: {e}")
            page.screenshot(path="crash_report.png")
            raise e

        finally:
            browser.close()

if __name__ == "__main__":
    run_stable_login()
