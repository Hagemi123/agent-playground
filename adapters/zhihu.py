"""
Zhihu Adapter for Agent Playground.
Handles authentication, question/answer discovery, trending topics, and interactions.
"""

import os
import time
from typing import Dict, Any, Optional
from core.browser import BrowserManager
from adapters.base import BaseAdapter

class ZhihuAdapter(BaseAdapter):
    SESSION_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "cookies", "zhihu_session.json"))
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
        """Check whether current session has logged in to Zhihu."""
        page = self.browser_manager.new_page()
        try:
            page.goto("https://www.zhihu.com/", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            
            # Check avatar / header
            avatar = page.locator('.AppHeader-profileEntry, img.Avatar, button.AppHeader-profile')
            is_logged_in = False
            if avatar.count() > 0 and avatar.first.is_visible():
                is_logged_in = True
                
            # Check cookies
            cookies = page.context.cookies()
            z_c0 = next((c['value'] for c in cookies if c['name'] == 'z_c0'), None)
            if z_c0:
                is_logged_in = True

            return {
                "logged_in": is_logged_in,
                "has_auth_token": bool(z_c0),
                "cookies_count": len(cookies)
            }
        finally:
            page.close()

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Attempt to log in to Zhihu with phone/email and password."""
        page = self.browser_manager.new_page()
        self.current_page = page
        screenshot_path = os.path.join(self.CAPTURES_DIR, "zhihu_login_state.png")

        try:
            print(f"[*] Navigating to Zhihu signin...")
            page.goto("https://www.zhihu.com/signin", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Switch to '密码登录'
            pwd_tab = page.locator('text="密码登录"').first
            if pwd_tab.is_visible():
                print("[*] Switching to password login tab...")
                pwd_tab.click()
                page.wait_for_timeout(1000)

            # Fill username
            print(f"[*] Entering credentials for {username}...")
            user_input = page.locator('input[name="username"]').first
            user_input.fill(username)

            # Fill password
            pwd_input = page.locator('input[name="password"]').first
            pwd_input.fill(password)
            page.wait_for_timeout(500)

            # Click submit button
            submit_btn = page.locator('button[type="submit"]').first
            print("[*] Submitting login form...")
            submit_btn.click()

            # Wait for response / captcha
            page.wait_for_timeout(4000)
            current_url = page.url
            page.screenshot(path=screenshot_path)

            # Check if login succeeded
            cookies = page.context.cookies()
            z_c0 = next((c['value'] for c in cookies if c['name'] == 'z_c0'), None)
            if z_c0 or "/signin" not in current_url:
                print(f"[+] Zhihu login succeeded! URL: {current_url}")
                self.browser_manager.save_storage_state(self.SESSION_FILE)
                return {
                    "success": True,
                    "status": "authenticated",
                    "url": current_url,
                    "screenshot": screenshot_path
                }

            # Check for error message or captcha
            content = page.content()
            error_msg = ""
            error_elem = page.locator('.SignFlowInput-error, .SignContainer-error')
            if error_elem.count() > 0 and error_elem.first.is_visible():
                error_msg = error_elem.first.inner_text().strip()

            challenge = ""
            if "NECaptcha" in content or page.locator('.yidun, .yidun_slider').count() > 0:
                challenge = "NetEase NECaptcha slider triggered"
            elif "验证码" in content:
                challenge = "Verification code / SMS prompt"

            return {
                "success": False,
                "status": "challenge_required" if challenge else "failed",
                "error": error_msg,
                "challenge": challenge,
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
