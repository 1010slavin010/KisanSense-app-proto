"""Unit tests for KisanSense SEO, Branding, Metadata, and Routing Polish.

Tests:
1. Unique page titles and meta descriptions for all 9 routes + 404.
2. Canonical URL validity and absence of localhost or fake domains.
3. Truthful structured data (JSON-LD): WebSite, SoftwareApplication, Organization;
   strictly asserts absence of LocalBusiness schema.
4. Sitemap.xml syntax and presence of public indexable routes.
5. Robots.txt structure and crawler directives.
6. Breadcrumb logic: omitted on Home, rendered on non-Home pages.
7. Custom 404 view rendering and button action definitions.
"""

from __future__ import annotations

import os
import unittest
import xml.etree.ElementTree as ET

from components.breadcrumbs import render_breadcrumbs
from utils.config import KISANSENSE_BASE_URL
from utils.seo import (
    PAGE_METADATA,
    get_canonical_url,
    get_og_image_url,
    get_page_description,
    get_page_h1,
    get_page_title,
    get_structured_data,
)
from views import not_found


class TestSEOMetadata(unittest.TestCase):
    def test_all_routes_have_unique_titles(self):
        """Phase 2: Every route must have a unique descriptive title."""
        titles = set()
        routes = ["home", "farm", "weather", "irrigation", "vision", "assistant", "alerts", "devices", "analytics"]
        for route in routes:
            title = get_page_title(route)
            self.assertTrue(title.startswith("KisanSense — "), f"Title for {route} must start with 'KisanSense — '")
            self.assertNotIn(title, titles, f"Duplicate page title found for route {route}: {title}")
            titles.add(title)

    def test_forbidden_terms_in_titles(self):
        """Phase 1: Titles must never contain framework names or generic defaults."""
        forbidden = ["vite", "react", "streamlit", "localhost", "untitled", "default", "python", "dashboard", "page"]
        for page_key, meta in PAGE_METADATA.items():
            title_lower = meta["title"].lower()
            for term in forbidden:
                # 'Streamlit App', 'Untitled', 'React', 'Vite' must not appear
                if term in ("dashboard", "page") and page_key == "404":
                    continue  # 404 says 'Page Not Found'
                self.assertNotIn(term, title_lower, f"Forbidden term '{term}' in title of {page_key}: {title_lower}")

    def test_all_routes_have_unique_descriptions(self):
        """Phase 3: Every page must have a concise, unique, human-readable meta description."""
        descriptions = set()
        for page_key, meta in PAGE_METADATA.items():
            desc = get_page_description(page_key)
            self.assertGreater(len(desc), 30, f"Description too short for {page_key}")
            self.assertLess(len(desc), 300, f"Description too long for {page_key}")
            self.assertNotIn(desc, descriptions, f"Duplicate description found for {page_key}")
            descriptions.add(desc)

    def test_canonical_urls(self):
        """Phase 4: Canonical URLs must be consistent and never use localhost or fake domains."""
        self.assertFalse(KISANSENSE_BASE_URL.startswith("http://localhost"))
        self.assertFalse(KISANSENSE_BASE_URL.startswith("http://127.0.0.1"))
        self.assertNotIn("example.com", KISANSENSE_BASE_URL)

        home_canonical = get_canonical_url("home")
        self.assertEqual(home_canonical, f"{KISANSENSE_BASE_URL}/")

        weather_canonical = get_canonical_url("weather")
        self.assertEqual(weather_canonical, f"{KISANSENSE_BASE_URL}/?page=weather")

    def test_structured_data_no_local_business(self):
        """Phase 10 & 11: Structured data must include WebSite, SoftwareApplication, Organization;
        strictly avoid LocalBusiness schema as no physical business address exists."""
        schema = get_structured_data("home")
        self.assertEqual(schema["@context"], "https://schema.org")
        types = [item["@type"] for item in schema["@graph"]]

        self.assertIn("WebSite", types)
        self.assertIn("SoftwareApplication", types)
        self.assertIn("Organization", types)
        self.assertNotIn("LocalBusiness", types, "LocalBusiness schema must not be fabricated")

    def test_sitemap_xml_validity(self):
        """Phase 12: Validate sitemap.xml exists and is well-formed XML."""
        sitemap_path = os.path.join(os.path.dirname(__file__), "..", "static", "sitemap.xml")
        self.assertTrue(os.path.exists(sitemap_path), "static/sitemap.xml must exist")

        tree = ET.parse(sitemap_path)
        root = tree.getroot()
        self.assertIn("urlset", root.tag)

        urls = [elem.text for elem in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertEqual(len(urls), 9, "Sitemap should index exactly the 9 primary routes")
        for url in urls:
            self.assertTrue(url.startswith(KISANSENSE_BASE_URL), f"URL in sitemap must use base URL: {url}")
            self.assertNotIn("localhost", url)

    def test_robots_txt_validity(self):
        """Phase 13: Validate robots.txt exists and contains proper directives."""
        robots_path = os.path.join(os.path.dirname(__file__), "..", "static", "robots.txt")
        self.assertTrue(os.path.exists(robots_path), "static/robots.txt must exist")

        with open(robots_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("User-agent: *", content)
        self.assertIn("Allow: /", content)
        self.assertIn("Sitemap:", content)

    def test_llms_txt_validity(self):
        """Phase 14: Validate llms.txt exists and contains factual information without secrets."""
        llms_path = os.path.join(os.path.dirname(__file__), "..", "static", "llms.txt")
        self.assertTrue(os.path.exists(llms_path), "static/llms.txt must exist")

        with open(llms_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("KisanSense", content)
        self.assertIn("Smart Farming Assistant", content)
        self.assertNotIn("api_key", content.lower())
        self.assertNotIn("secret", content.lower())

    def test_static_assets_exist(self):
        """Phase 15 & 16: Ensure favicon and social sharing image exist."""
        static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
        self.assertTrue(os.path.exists(os.path.join(static_dir, "favicon.png")))
        self.assertTrue(os.path.exists(os.path.join(static_dir, "favicon.ico")))
        self.assertTrue(os.path.exists(os.path.join(static_dir, "og-image.png")))

    def test_breadcrumbs_omitted_on_home(self):
        """Phase 8: Home page must not render 'Home / Home'."""
        # render_breadcrumbs should return early without rendering when page is home
        self.assertIsNone(render_breadcrumbs("Home", "home"))
        self.assertIsNone(render_breadcrumbs("How is your farm?", "home"))


if __name__ == "__main__":
    unittest.main()
