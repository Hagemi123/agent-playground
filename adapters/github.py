"""
GitHub Adapter for Agent Playground.
Handles authentication, session persistence, and repository/user interaction.
"""

import os
import time
from typing import Dict, Any, Optional
from core.browser import BrowserManager

class GitHubAdapter:
    SESSION_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "cookies", "github_session.json"))
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
        """Check whether the current session is already logged in to GitHub."""
        page = self.browser_manager.new_page()
        try:
            page.goto("https://github.com/", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            
            # Check meta tag or user button
            meta_login = page.locator('meta[name="user-login"]').get_attribute("content")
            if meta_login and meta_login.strip():
                return {"logged_in": True, "username": meta_login.strip()}
            
            # Check if sign in button is visible
            sign_in_btn = page.locator('a[href="/login"]').first
            if sign_in_btn.is_visible():
                return {"logged_in": False, "username": None}
                
            return {"logged_in": False, "username": None}
        finally:
            page.close()

    def login(self, email_or_username: str, password: str) -> Dict[str, Any]:
        """Attempt to log in to GitHub with credentials."""
        page = self.browser_manager.new_page()
        self.current_page = page
        screenshot_path = os.path.join(self.CAPTURES_DIR, "github_login_status.png")

        try:
            print(f"Navigating to GitHub login page...")
            page.goto("https://github.com/login", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)

            # Fill username & password
            print("Entering credentials...")
            page.fill('input[name="login"]', email_or_username)
            page.fill('input[name="password"]', password)
            
            # Click sign-in
            page.click('input[type="submit"]')
            
            # Wait for response/navigation
            page.wait_for_timeout(4000)
            current_url = page.url
            print(f"Post-submit URL: {current_url}")

            # Take screenshot of current state
            page.screenshot(path=screenshot_path)

            # Check if login succeeded
            meta_login = page.locator('meta[name="user-login"]').get_attribute("content")
            if meta_login and meta_login.strip():
                print(f"Login successful as {meta_login}!")
                self.browser_manager.save_storage_state(self.SESSION_FILE)
                return {
                    "success": True,
                    "status": "authenticated",
                    "username": meta_login,
                    "screenshot": screenshot_path
                }

            # Check for error banner
            error_flash = page.locator('.flash-error, .flash-warn')
            if error_flash.count() > 0 and error_flash.first.is_visible():
                error_text = error_flash.first.inner_text().strip()
                return {
                    "success": False,
                    "status": "login_failed",
                    "error": error_text,
                    "url": current_url,
                    "screenshot": screenshot_path
                }

            # Check for 2FA / Device verification
            if "two-factor" in current_url or "verified-device" in current_url:
                otp_input = page.locator('input[name="otp"], input#app_totp, input#otp')
                prompt_text = "Two-factor authentication required."
                header = page.locator('h1, h2, .subhead-heading')
                if header.count() > 0:
                    prompt_text = header.first.inner_text().strip()
                
                return {
                    "success": False,
                    "status": "needs_2fa",
                    "prompt": prompt_text,
                    "url": current_url,
                    "screenshot": screenshot_path
                }

            # Check for CAPTCHA
            if "captcha" in page.content().lower():
                return {
                    "success": False,
                    "status": "needs_captcha",
                    "url": current_url,
                    "screenshot": screenshot_path
                }

            return {
                "success": False,
                "status": "unknown",
                "url": current_url,
                "screenshot": screenshot_path
            }

        except Exception as e:
            page.screenshot(path=screenshot_path)
            return {
                "success": False,
                "status": "exception",
                "error": str(e),
                "screenshot": screenshot_path
            }

    def submit_2fa(self, otp_code: str) -> Dict[str, Any]:
        """Submit 2FA / OTP code if currently on the 2FA page."""
        screenshot_path = os.path.join(self.CAPTURES_DIR, "github_2fa_result.png")
        if not self.current_page or self.current_page.is_closed():
            return {"success": False, "error": "No active page session for 2FA."}

        page = self.current_page
        try:
            # Find OTP input
            otp_input = page.locator('input[name="otp"], input#app_totp, input#otp').first
            if not otp_input.is_visible():
                return {"success": False, "error": "OTP input field not found."}

            otp_input.fill(otp_code.strip())
            
            # Submit button if needed
            verify_btn = page.locator('button[type="submit"], input[type="submit"]')
            if verify_btn.count() > 0:
                verify_btn.first.click()

            page.wait_for_timeout(4000)
            page.screenshot(path=screenshot_path)

            meta_login = page.locator('meta[name="user-login"]').get_attribute("content")
            if meta_login and meta_login.strip():
                self.browser_manager.save_storage_state(self.SESSION_FILE)
                return {
                    "success": True,
                    "status": "authenticated",
                    "username": meta_login,
                    "screenshot": screenshot_path
                }

            return {
                "success": False,
                "status": "verification_failed",
                "url": page.url,
                "screenshot": screenshot_path
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_repositories(self, query: str, sort: str = "stars", limit: int = 5) -> Dict[str, Any]:
        """Search GitHub repositories using the authenticated session."""
        page = self.browser_manager.new_page()
        encoded_query = query.replace(" ", "+")
        url = f"https://github.com/search?q={encoded_query}&type=repositories&s={sort}"
        screenshot_path = os.path.join(self.CAPTURES_DIR, f"search_{query.replace(' ', '_')}.png")

        try:
            print(f"Searching GitHub: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            page.screenshot(path=screenshot_path)

            results = []
            # In GitHub's modern search UI, repo cards are items with repository links
            cards = page.locator('div[data-testid="results-list"] > div, div.Box-row')
            count = cards.count()
            if count == 0:
                # Fallback selector for alternative layout
                cards = page.locator('div.search-title, a[class*="search-match"]')
            
            # Extract links matching owner/repo pattern
            links = page.locator('a[href^="/"][data-testid="search-result-title"], a.v-align-middle')
            link_count = links.count()
            print(f"Found {link_count} potential repository links.")

            for i in range(min(link_count, limit)):
                repo_link = links.nth(i)
                text = repo_link.inner_text().strip()
                href = repo_link.get_attribute("href")
                if href and href.startswith("/"):
                    repo_full_name = href.strip("/")
                    # Avoid non-repo links like search/login
                    if "/" in repo_full_name and not repo_full_name.startswith("search"):
                        results.append({
                            "name": text or repo_full_name,
                            "repo": repo_full_name,
                            "url": f"https://github.com/{repo_full_name}"
                        })

            return {
                "success": True,
                "query": query,
                "count": len(results),
                "repositories": results,
                "screenshot": screenshot_path
            }
        except Exception as e:
            return {"success": False, "error": str(e), "screenshot": screenshot_path}
        finally:
            page.close()

    def star_repo(self, repo_full_name: str) -> Dict[str, Any]:
        """Star a repository on GitHub."""
        page = self.browser_manager.new_page()
        url = f"https://github.com/{repo_full_name}"
        screenshot_path = os.path.join(self.CAPTURES_DIR, f"star_{repo_full_name.replace('/', '_')}.png")

        try:
            print(f"Navigating to repo: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Locate Star button
            # GitHub star button is usually inside a form with action ending in /star or /unstar
            star_btn = page.locator('button[data-hydro-click*="star"], form[action$="/star"] button, button:has-text("Star")').first
            unstar_btn = page.locator('form[action$="/unstar"] button, button:has-text("Starred")').first

            already_starred = False
            if unstar_btn.is_visible():
                print(f"Repository {repo_full_name} is already starred.")
                already_starred = True
            elif star_btn.is_visible():
                print(f"Clicking Star button for {repo_full_name}...")
                star_btn.click()
                page.wait_for_timeout(2000)
                # Verify it changed to Starred / unstar
                if unstar_btn.is_visible() or "starred" in page.content().lower():
                    print("Star action verified!")

            page.screenshot(path=screenshot_path)
            self.browser_manager.save_storage_state(self.SESSION_FILE)

            return {
                "success": True,
                "repo": repo_full_name,
                "already_starred": already_starred,
                "screenshot": screenshot_path
            }
        except Exception as e:
            return {"success": False, "error": str(e), "screenshot": screenshot_path}
        finally:
            page.close()

    def create_repository(self, repo_name: str, description: str = "") -> Dict[str, Any]:
        """Create a new public repository on GitHub."""
        page = self.browser_manager.new_page()
        screenshot_path = os.path.join(self.CAPTURES_DIR, f"created_repo_{repo_name}.png")
        try:
            print(f"[*] Navigating to GitHub new repository page...")
            page.goto("https://github.com/new", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Enter repo name
            name_input = page.locator('input#repository-name-input, input[data-testid="repository-name-input"]').first
            print(f"[*] Typing repo name: {repo_name}...")
            name_input.fill(repo_name)
            page.wait_for_timeout(1000)

            # Enter description if provided
            if description:
                desc_input = page.locator('input[name="Description"], input[id*="description"]').first
                if desc_input.is_visible():
                    print(f"[*] Typing description: {description}...")
                    desc_input.fill(description)
                    page.wait_for_timeout(500)

            # Wait for button to be enabled
            create_btn = page.locator('button[type="submit"]:has-text("Create repository"), button:has-text("Create repository")').first
            page.wait_for_timeout(2000)

            print("[*] Clicking 'Create repository' button...")
            create_btn.click()
            
            # Wait for redirect to the new repo page
            page.wait_for_timeout(5000)
            current_url = page.url
            print(f"[+] Post-creation URL: {current_url}")

            page.screenshot(path=screenshot_path)
            
            is_success = f"/{repo_name}" in current_url
            return {
                "success": is_success,
                "repo_name": repo_name,
                "url": current_url,
                "screenshot": screenshot_path
            }
        except Exception as e:
            page.screenshot(path=screenshot_path)
            return {"success": False, "error": str(e), "screenshot": screenshot_path}
        finally:
            page.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

