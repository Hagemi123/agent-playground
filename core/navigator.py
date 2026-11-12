"""
Autonomous Web Navigator.
Combines browser automation, dynamic scrolling, visual snapshotting,
and structured extraction inspired by Crawl4AI and Browser-Use.
"""

import os
import time
from typing import Dict, Any, List, Optional
from core.browser import BrowserManager
from core.extractor import WebExtractor

class WebNavigator:
    def __init__(self, headless: bool = True):
        self.browser_manager = BrowserManager(headless=headless)

    def explore_url(self, url: str, scroll_times: int = 2, wait_seconds: float = 2.0, capture_name: str = "web_explore") -> Dict[str, Any]:
        """Navigate to URL, dynamically scroll to load lazy content, take screenshot and extract structured content."""
        with self.browser_manager as bm:
            page = bm.new_page()
            try:
                print(f"[*] Navigating to: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(int(wait_seconds * 1000))

                # Dynamic scroll to trigger lazy loading / infinite feeds
                for s in range(scroll_times):
                    page.mouse.wheel(0, 1000)
                    page.wait_for_timeout(1000)

                # Capture full screenshot
                captures_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "captures"))
                os.makedirs(captures_dir, exist_ok=True)
                screenshot_path = os.path.join(captures_dir, f"{capture_name}.png")
                page.screenshot(path=screenshot_path)

                # Get DOM content
                content_html = page.content()
                structured_data = WebExtractor.clean_html_to_markdown(content_html, base_url=url)
                structured_data["url"] = url
                structured_data["screenshot"] = screenshot_path

                return {
                    "success": True,
                    "data": structured_data
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
            finally:
                page.close()
