"""
Browser automation engine using Playwright.
Supports headless / visible mode using system Chrome or Edge.
"""

import os
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

class BrowserManager:
    def __init__(self, headless: bool = True, channel: str = "chrome", storage_state: Optional[str] = None):
        self.headless = headless
        self.channel = channel
        self.storage_state = storage_state
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    def start(self):
        """Starts the browser instance."""
        if not self.playwright:
            self.playwright = sync_playwright().start()
            # Try specified channel (chrome), fallback to msedge if chrome fails
            try:
                self.browser = self.playwright.chromium.launch(
                    headless=self.headless,
                    channel=self.channel,
                    args=["--disable-blink-features=AutomationControlled"]
                )
            except Exception as e:
                # Fallback to Edge
                print(f"Failed to launch with channel {self.channel}: {e}. Retrying with msedge...")
                self.browser = self.playwright.chromium.launch(
                    headless=self.headless,
                    channel="msedge",
                    args=["--disable-blink-features=AutomationControlled"]
                )
            
            context_args = {
                "viewport": {"width": 1280, "height": 800},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            }
            if self.storage_state and os.path.exists(self.storage_state):
                context_args["storage_state"] = self.storage_state
                
            self.context = self.browser.new_context(**context_args)
        return self

    def save_storage_state(self, path: str):
        """Saves session cookies and local storage."""
        if self.context:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            self.context.storage_state(path=path)

    def new_page(self) -> Page:
        if not self.context:
            self.start()
        return self.context.new_page()

    def navigate_and_capture(self, url: str, screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """Navigate to URL, extract basic metadata, and optionally save screenshot."""
        page = self.new_page()
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = page.title()
            
            # If screenshot requested, ensure directory exists
            if screenshot_path:
                os.makedirs(os.path.dirname(os.path.abspath(screenshot_path)), exist_ok=True)
                page.screenshot(path=screenshot_path)
            
            status = response.status if response else None
            return {
                "url": url,
                "title": title,
                "status": status,
                "screenshot": screenshot_path if screenshot_path and os.path.exists(screenshot_path) else None
            }
        finally:
            page.close()

    def stop(self):
        """Clean up browser resources."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
            self.playwright = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
