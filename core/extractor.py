"""
Smart content extractor for web pages.
Converts dynamic web page DOM into clean, structured Markdown, links, and media.
"""

from typing import Dict, Any, List
from bs4 import BeautifulSoup

class WebExtractor:
    @staticmethod
    def clean_html_to_markdown(html_content: str, base_url: str = "") -> Dict[str, Any]:
        """Parse HTML, strip noise (scripts, styles, ads), and return readable text & metadata."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Title
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        # Remove irrelevant elements
        for tag in soup(["script", "style", "noscript", "svg", "iframe", "header", "footer"]):
            tag.decompose()

        # Extract meta tags
        meta_description = ""
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if desc_tag and desc_tag.get("content"):
            meta_description = desc_tag["content"].strip()

        # Extract main text
        body = soup.find("main") or soup.find("article") or soup.find("body") or soup
        text = body.get_text(separator="\n", strip=True) if body else ""

        # Extract links
        links = []
        for a in soup.find_all("a", href=True):
            link_text = a.get_text(strip=True)
            href = a["href"]
            if link_text and href and not href.startswith("javascript:"):
                links.append({"text": link_text, "url": href})

        return {
            "title": title,
            "description": meta_description,
            "text_sample": text[:1500],
            "total_text_length": len(text),
            "links_count": len(links),
            "top_links": links[:10]
        }
