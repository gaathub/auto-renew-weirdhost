import os
import time
import pyotp
from playwright.sync_api import sync_playwright

# --- 环境变量 (云端运行必须用环境变量) ---
DISCORD_EMAIL = os.environ["DIS_EMAIL"]
DISCORD_PASSWORD = os.environ["DIS_PASSWORD"]
TWO_FA_SECRET = os.environ["DIS_SECRET"].replace(" ", "")

LOGIN_URL = "https://hub.weirdhost.xyz/auth/login"
TARGET_SERVER_URL = "https://hub.weirdhost.xyz/server/10a4aaad"

def run_strict_login():
    print("🚀 [严格登录版] 启动...")
    with sync_playwright() as p:
        # 云端必须是 headless=True
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 拦截 Discord APP 唤起
        page.route("**/*", lambda route: route.abort() if "discord://" in route.request.url else route.continue_())

        try:
            # --- 1. 进入登录页 ---
            print("1️⃣ 访问登录页...")
            page.goto(LOGIN_URL)
            page.wait_for_load_state("networkidle")

            if "login" in page.url:
                print("   -> 检测到登录界面，开始执行操作...")

                # --- 步骤 A: 勾选条款 (重中之重) ---
                print("   -> [A] 尝试勾选条款...")
                try:
                    checkbox = page.locator("input[type='checkbox']")
                    checkbox.wait_for(state="visible", timeout=5000)
                    # 强制勾选
                    checkbox.check(force=True)
                    time.sleep(1) # 等一秒确保生效
                    
                    # 再次检查是否真的勾上了
                    if not checkbox.is_checked():
                        print("   ⚠️ 条款似乎没勾上，尝试 JS 强制点击...")
                        page.evaluate("document.querySelector(\"input[type='checkbox']\").click()")
                except Exception as e:
                    print(f"   ⚠️ 勾选条款出现问题 (可能已默认勾选): {e}")

                # --- 步骤 B: 点击 Discord 按钮 ---
                print("   -> [B] 点击 Discord 登录按钮...")
                # 优先寻找 href 包含 discord 的链接 (最稳)
                discord_btn = page.locator("a[href*='discord']").first
                
                # 点击并等待 URL 变化
                with page.expect_navigation(url=lambda url: "discord.com" in url or "weirdhost" in url, timeout=15000):
                    if discord_btn.is_visible():
                        discord_btn.click()
                    else:
                        # 备用：找文字
                        page.click("text=디스코드로 로그인하기", timeout=3000)
                
                print("   -> ✅ 成功跳转，正在等待 Discord 页面加载...")
                page.wait_for_load_state("domcontentloaded")

                # --- 步骤 C: 处理 Discord 登录 ---
                # 检查是否进入了 Discord
                if "discord.com" in page.url:
                    print("2️⃣ 进入 Discord 验证流程...")
                    
                    # 1. 关掉 APP 弹窗
                    if page.locator("button:has-text('继续使用')").count() > 0:
                        print("   -> 关闭 APP 弹窗")
                        page.locator("button:has-text('继续使用')").click()

                    # 2. 填账号
                    if page.locator("input[name='email']").is_visible():
                        print("   -> 输入账号密码...")
                        page.fill("input[name='email']", DISCORD_EMAIL)
                        page.fill("input[name='password']", DISCORD_PASSWORD)
                        page.click("button[type='submit']")
                        time.sleep(3) # 等待跳转

                    # 3. 填 2FA
                    if page.locator("input[autocomplete='one-time-code']").count() > 0:
                        print("   -> 输入 2FA 验证码...")
                        totp = pyotp.TOTP(TWO_FA_SECRET)
                        page.fill("input[autocomplete='one-time-code']", totp.now())
                        page.click("button[type='submit']")
                        time.sleep(3)

                    # 4. 🔥🔥🔥 点击授权 (Authorize) 🔥🔥🔥
                    # 必须等到这个按钮出现
                    print("   -> 等待授权按钮...")
                    try:
                        auth_btn = page.locator("button:has-text('Authorize'), button:has-text('授权'), button:has-text('승인')").last
                        auth_btn.wait_for(state="visible", timeout=10000)
                        auth_btn.click()
                        print("   -> ✅ 已点击授权按钮！")
                    except:
                        print("   -> ⚠️ 未找到授权按钮，可能已经自动授权或跳过")

            # --- 步骤 D: 验证登录结果 ---
            print("3️⃣ 等待跳转回 WeirdHost...")
            try:
                # 等待 URL 不包含 login
                page.wait_for_url(lambda url: "login" not in url, timeout=20000)
                print("   -> 跳转完成")
            except:
                print("   ⚠️ 跳转超时，检查当前页面...")

            # 再次确认：如果我们还在登录页，说明失败了！
            if "login" in page.url:
                print("❌❌❌ 严重错误：依然停留在登录页！登录失败！")
                print("   -> 可能是条款没勾上，或者 Discord 授权没点到。")
                page.screenshot(path="login_failed.png")
                raise Exception("Login Failed")
            
            # --- 步骤 E: 续费 ---
            print(f"4️⃣ 前往服务器页面: {TARGET_SERVER_URL}")
            page.goto(TARGET_SERVER_URL)
            page.wait_for_load_state("domcontentloaded")
            
            # 再次检查是不是被弹回登录页了 (你的截图就是这种情况)
            if "login" in page.url:
                print("❌❌❌ 访问服务器页面被弹回登录页！Session 无效。")
                page.screenshot(path="session_lost.png")
                raise Exception("Session Invalid")

            print("5️⃣ 寻找续费按钮...")
            try:
                renew_btn = page.locator("span").filter(has_text="시간추가").first
                renew_btn.wait_for(state="visible", timeout=10000)
                renew_btn.scroll_into_view_if_needed()
                renew_btn.click()
                print("   -> 按钮已点击")
                
                # 检查结果
                try:
                    error_msg = page.locator("text=You can't renew")
                    error_msg.wait_for(state="visible", timeout=5000)
                    print("❌ [结果] 还没到续费时间")
                except:
                    print("✅ [结果] 续费成功")
                    
            except Exception as e:
                print(f"❌ 未找到续费按钮 (可能页面结构变了或未加载): {e}")
                page.screenshot(path="no_button.png")
                raise e

        except Exception as e:
            print(f"💥 运行崩溃: {e}")
            page.screenshot(path="crash.png")
            raise e

        finally:
            browser.close()

if __name__ == "__main__":
    run_strict_login()
