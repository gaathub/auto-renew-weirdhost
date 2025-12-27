import time
import pyotp
from playwright.sync_api import sync_playwright

# --- 🔴 配置区域 ---
DISCORD_EMAIL = "cbdyyk@outlook.com"
DISCORD_PASSWORD = "YOUR_PASSWORD_HERE"  # <--- ⚠️ 填回密码
TWO_FA_SECRET = "f7he xstx 43co tvlc lwmd nad7 vp4i ibya".replace(" ", "")

# 网址
LOGIN_URL = "https://hub.weirdhost.xyz/auth/login"
TARGET_SERVER_URL = "https://hub.weirdhost.xyz/server/10a4aaad"

def run_smart_renew():
    print("🚀 [智能缓存版] 启动...")
    with sync_playwright() as p:
        # --- 🔥 关键点 1: 恢复使用 user_data_dir (保存缓存) ---
        # 只有保存了 Cookie，Discord 才不会每次都弹验证码
        browser = p.chromium.launch_persistent_context(
            user_data_dir="user_data", 
            headless=False,  # 本地运行设为 False，方便你手动点验证码
            viewport={'width': 1366, 'height': 768},
            args=["--disable-blink-features=AutomationControlled"] # 尝试隐藏自动化特征
        )
        
        page = browser.pages[0]
        # 拦截 Discord APP 唤起
        page.route("**/*", lambda route: route.abort() if "discord://" in route.request.url else route.continue_())

        print(f"🌐 [1] 访问 WeirdHost...")
        try:
            page.goto(LOGIN_URL, timeout=60000)
            page.wait_for_load_state("domcontentloaded")
        except:
            print("   ⚠️ 页面加载超时，尝试继续...")

        # --- 🔥 关键点 2: 智能判断是否需要登录 ---
        # 如果 URL 里没有 'login'，说明 Cookie 还有效，直接跳过登录！
        if "login" not in page.url:
            print("🎉 [缓存有效] 检测到已登录，直接跳过登录步骤！")
        else:
            print("🔒 [缓存失效] 检测到登录页，开始登录流程...")

            # [A] 勾选条款
            try:
                checkbox = page.locator("input[type='checkbox']")
                if checkbox.count() > 0 and not checkbox.is_checked():
                    checkbox.check(force=True)
                    time.sleep(0.5)
            except:
                pass

            # [B] 点击 Discord 登录
            print("   -> 点击 Discord 登录按钮...")
            discord_btn = page.locator("a[href*='discord']").first
            if not discord_btn.is_visible():
                discord_btn = page.locator("text=디스코드로 로그인하기").first
            
            discord_btn.click()
            
            # 等待跳转
            try:
                page.wait_for_url(lambda url: "discord.com" in url, timeout=20000)
                print("   -> 已跳转至 Discord")
            except:
                print("   ⚠️ 跳转超时或已自动回调")

            # [C] Discord 登录 (如果需要)
            if "discord.com" in page.url:
                page.wait_for_load_state("domcontentloaded")
                time.sleep(2)
                
                # 1. 检查是否需要输入密码
                if page.locator("input[name='email']").is_visible():
                    print("   -> 输入账号密码...")
                    page.fill("input[name='email']", DISCORD_EMAIL)
                    page.fill("input[name='password']", DISCORD_PASSWORD)
                    page.click("button[type='submit']")
                    time.sleep(3)
                
                # 🔥🔥🔥 [关键] 检测人机验证 (hCaptcha) 🔥🔥🔥
                # 如果出现 iframe 验证码，脚本会暂停等待你手动处理
                if page.locator("iframe[src*='hcaptcha']").count() > 0 or page.locator("iframe[src*='cloudflare']").count() > 0:
                    print("\n⚠️⚠️⚠️ 检测到人机验证！请在浏览器窗口中手动完成验证！⚠️⚠️⚠️")
                    print("waiting for manual captcha solution...")
                    # 死等，直到验证码消失或跳转
                    try:
                        page.wait_for_url(lambda url: "weirdhost" in url or "one-time-code" in page.content(), timeout=120000)
                        print("   -> ✅ 验证似乎已通过")
                    except:
                        print("   -> 等待超时，尝试继续...")

                # 2. 检查 2FA
                if page.locator("input[autocomplete='one-time-code']").count() > 0:
                    print("   -> 输入 2FA...")
                    totp = pyotp.TOTP(TWO_FA_SECRET)
                    page.fill("input[autocomplete='one-time-code']", totp.now())
                    page.click("button[type='submit']")
                    time.sleep(3)

                # 3. 检查授权
                try:
                    auth_btn = page.locator("button:has-text('Authorize'), button:has-text('授权'), button:has-text('승인')").last
                    if auth_btn.is_visible():
                        auth_btn.click()
                        print("   -> 点击授权")
                except:
                    pass

                # 等待回调
                print("⏳ 等待跳转回控制台...")
                try:
                    page.wait_for_url(lambda url: "weirdhost.xyz" in url and "discord" not in url, timeout=60000)
                except:
                    pass

        # --- 第二部分: 续费 ---
        print("🧭 [2] 前往服务器页面...")
        page.goto(TARGET_SERVER_URL)
        page.wait_for_load_state("domcontentloaded")

        # 再次检查是否被踢回登录页
        if "login" in page.url:
            print("❌❌❌ 失败：Session 丢失，需重新登录。")
            # 如果这里失败了，说明缓存有问题，下次运行会自动重新登录
        else:
            print("⚡ [3] 寻找续费按钮...")
            try:
                renew_btn = page.locator("span:has-text('시간추가')").first
                renew_btn.wait_for(state="visible", timeout=15000)
                renew_btn.scroll_into_view_if_needed()
                renew_btn.click()
                print("   -> 🔘 按钮已点击")
                
                try:
                    page.locator("text=You can't renew").wait_for(state="visible", timeout=5000)
                    print("   -> ❌ 还没到时间")
                except:
                    print("   -> ✅ 续费成功！")
            except Exception as e:
                print(f"   -> ⚠️ 未找到按钮或出错: {e}")

        print("🏁 任务结束")
        # browser.close() # 建议本地调试时注释掉这行，方便观察

if __name__ == "__main__":
    run_smart_renew()
