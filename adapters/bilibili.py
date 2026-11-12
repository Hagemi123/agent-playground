"""
Bilibili Adapter for Agent Playground.
Handles authentication, video/stream discovery, dynamic feeds, and interaction.
"""

import os
import time
from typing import Dict, Any, Optional
from core.browser import BrowserManager
from adapters.base import BaseAdapter

class BilibiliAdapter(BaseAdapter):
    SESSION_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "cookies", "bilibili_session.json"))
    CAPTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "captures"))

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser_manager = BrowserManager(headless=self.headless, storage_state=self.SESSION_FILE)
        self.current_page = None

    def start(self):
        self.browser_manager.start()
        return self

    def close(self):
        self.browser_manager.stop()

    def check_login_status(self) -> Dict[str, Any]:
        """Check whether current session has logged in to Bilibili."""
        page = self.browser_manager.new_page()
        try:
            page.goto("https://www.bilibili.com/", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            
            # Check avatar or user nav
            avatar = page.locator('.header-avatar-wrap, .bili-avatar, a.header-entry-avatar')
            is_logged_in = False
            username = None
            if avatar.count() > 0 and avatar.first.is_visible():
                is_logged_in = True
                
            # Double check cookies
            cookies = page.context.cookies()
            dede_user_id = next((c['value'] for c in cookies if c['name'] == 'DedeUserID'), None)
            if dede_user_id:
                is_logged_in = True
                username = f"UID:{dede_user_id}"

            return {
                "logged_in": is_logged_in,
                "username": username,
                "cookies_count": len(cookies)
            }
        finally:
            page.close()

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Attempt to log in with username/phone and password."""
        page = self.browser_manager.new_page()
        self.current_page = page
        screenshot_path = os.path.join(self.CAPTURES_DIR, "bilibili_login_state.png")

        try:
            print(f"[*] Navigating to Bilibili login...")
            page.goto("https://passport.bilibili.com/login", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Ensure '密码登录' is active
            pwd_tab = page.locator('text="密码登录"').first
            if pwd_tab.is_visible():
                pwd_tab.click()
                page.wait_for_timeout(500)

            # Enter username & password
            print(f"[*] Typing credentials for {username}...")
            user_input = page.locator('input[placeholder*="账号"], input[placeholder*="手机号"]').first
            user_input.fill(username)
            
            pwd_input = page.locator('input[placeholder*="密码"], input[type="password"]').first
            pwd_input.fill(password)
            page.wait_for_timeout(500)

            # Check if there's a login button
            login_btn = page.locator('.btn_primary, button:has-text("登录"), div.btn-box:has-text("登录"), .login-btn').first
            print("[*] Clicking login button...")
            login_btn.click()
            
            # Wait for response / captcha to appear
            page.wait_for_timeout(4000)
            current_url = page.url
            page.screenshot(path=screenshot_path)

            # Check if logged in
            cookies = page.context.cookies()
            dede_user_id = next((c['value'] for c in cookies if c['name'] == 'DedeUserID'), None)
            if dede_user_id or "passport.bilibili.com/login" not in current_url:
                print(f"[+] Login succeeded! UID: {dede_user_id}")
                self.browser_manager.save_storage_state(self.SESSION_FILE)
                return {
                    "success": True,
                    "status": "authenticated",
                    "uid": dede_user_id,
                    "screenshot": screenshot_path
                }

            # Check for Geetest puzzle / SMS / error text
            content = page.content()
            error_hint = ""
            if "geetest" in content.lower() or page.locator('.geetest_radar_tip, .geetest_popup_wrap, .geetest_box').count() > 0:
                error_hint = "Geetest verification/puzzle triggered"
            elif "短信" in content or "验证码" in content:
                error_hint = "SMS or graphic verification required"

            return {
                "success": False,
                "status": "challenge_required" if error_hint else "failed",
                "challenge": error_hint,
                "url": current_url,
                "screenshot": screenshot_path
            }
        except Exception as e:
            page.screenshot(path=screenshot_path)
            return {
                "success": False,
                "status": "error",
                "error": str(e),
                "screenshot": screenshot_path
            }

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
