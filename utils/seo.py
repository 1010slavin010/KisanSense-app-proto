"""SEO and Web Quality Metadata utilities for KisanSense.

Manages dynamic page titles, unique meta descriptions, canonical URLs,
Open Graph/Twitter card tags, structured data (JSON-LD), and parent head injection.
"""

from __future__ import annotations

import json
import streamlit as st
from utils.config import KISANSENSE_BASE_URL, APP_NAME

PAGE_METADATA: dict[str, dict[str, str]] = {
    "home": {
        "title": "KisanSense — Smart Farming Assistant",
        "h1": "How is your farm?",
        "description": (
            "AI-powered smart farming assistance for monitoring soil moisture, "
            "weather, crop health, irrigation and farm conditions."
        ),
        "path": "/",
    },
    "farm": {
        "title": "KisanSense — Camera / Crop Scan",
        "h1": "Camera / Crop Scan",
        "description": (
            "Upload a plant or leaf photo or use your camera to scan crop "
            "health and detect visible plant stress."
        ),
        "path": "/?page=farm",
    },
    "weather": {
        "title": "KisanSense — Farm Weather",
        "h1": "Farm Weather",
        "description": (
            "Monitor farm weather conditions and understand how temperature, "
            "humidity and rainfall may affect your crops."
        ),
        "path": "/?page=weather",
    },
    "irrigation": {
        "title": "KisanSense — Smart Irrigation",
        "h1": "Smart Irrigation",
        "description": (
            "Get clear irrigation guidance based on soil moisture, sensor "
            "conditions and farm weather context."
        ),
        "path": "/?page=irrigation",
    },
    "vision": {
        "title": "KisanSense — Crop Health",
        "h1": "Crop Health",
        "description": (
            "Screen crop images for visible plant health symptoms and receive "
            "conservative farming guidance."
        ),
        "path": "/?page=vision",
    },
    "assistant": {
        "title": "KisanSense — Farming Assistant",
        "h1": "KisanSense Assistant",
        "description": (
            "Ask KisanSense about crops, soil, irrigation, weather and current "
            "farm conditions."
        ),
        "path": "/?page=assistant",
    },
    "alerts": {
        "title": "KisanSense — Farm Alerts",
        "h1": "Farm Alerts",
        "description": (
            "Review important KisanSense farm alerts, sensor warnings and crop "
            "health observations."
        ),
        "path": "/?page=alerts",
    },
    "devices": {
        "title": "KisanSense — IoT Devices",
        "h1": "Farm Devices",
        "description": (
            "Monitor KisanSense sensor connectivity, battery status, signal "
            "strength and device health."
        ),
        "path": "/?page=devices",
    },
    "analytics": {
        "title": "KisanSense — Farm Analytics",
        "h1": "Farm Analytics",
        "description": (
            "Review KisanSense farm telemetry trends, operational metrics and "
            "historical observations."
        ),
        "path": "/?page=analytics",
    },
    "404": {
        "title": "KisanSense — Page Not Found",
        "h1": "Page not found",
        "description": (
            "The page you're looking for doesn't exist or may have moved. "
            "Return to KisanSense Home or Farm Profile."
        ),
        "path": "/?page=404",
    },
}


def get_page_title(page_key: str) -> str:
    """Return the unique browser title for the specified page."""
    meta = PAGE_METADATA.get(page_key, PAGE_METADATA["404"])
    return meta["title"]


def get_page_description(page_key: str) -> str:
    """Return the unique meta description for the specified page."""
    meta = PAGE_METADATA.get(page_key, PAGE_METADATA["404"])
    return meta["description"]


def get_page_h1(page_key: str) -> str:
    """Return the canonical single H1 text for the specified page."""
    meta = PAGE_METADATA.get(page_key, PAGE_METADATA["404"])
    return meta["h1"]


def get_canonical_url(page_key: str) -> str:
    """Return the absolute canonical URL for the specified page."""
    meta = PAGE_METADATA.get(page_key, PAGE_METADATA["404"])
    path = meta["path"]
    if path == "/":
        return f"{KISANSENSE_BASE_URL}/"
    return f"{KISANSENSE_BASE_URL}{path}"


def get_og_image_url() -> str:
    """Return the absolute URL to the Open Graph social sharing image."""
    return f"{KISANSENSE_BASE_URL}/app/static/og-image.png"


def get_structured_data(page_key: str) -> dict:
    """Return truthful JSON-LD structured data for the page.

    Includes WebSite, SoftwareApplication, and Organization schemas.
    Strictly avoids LocalBusiness schema as no physical business address exists.
    """
    canonical_url = get_canonical_url(page_key)
    meta = PAGE_METADATA.get(page_key, PAGE_METADATA["404"])

    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": f"{KISANSENSE_BASE_URL}/#website",
                "url": f"{KISANSENSE_BASE_URL}/",
                "name": APP_NAME,
                "description": PAGE_METADATA["home"]["description"],
            },
            {
                "@type": "SoftwareApplication",
                "@id": f"{KISANSENSE_BASE_URL}/#app",
                "name": APP_NAME,
                "applicationCategory": "Agricultural Technology / Smart Farming",
                "operatingSystem": "Web Browser",
                "url": canonical_url,
                "description": meta["description"],
                "image": get_og_image_url(),
            },
            {
                "@type": "Organization",
                "@id": f"{KISANSENSE_BASE_URL}/#organization",
                "name": APP_NAME,
                "url": f"{KISANSENSE_BASE_URL}/",
                "logo": f"{KISANSENSE_BASE_URL}/app/static/favicon.png",
                "description": "Smart farming assistance and environmental telemetry intelligence.",
            },
        ],
    }


def inject_seo_head(page_key: str) -> None:
    """Inject dynamic SEO meta tags, canonical link, and JSON-LD into the document.

    Because Streamlit runs in an iframe/SPA, this updates the top-level parent
    window head when accessible while also declaring iframe meta elements.
    """
    meta = PAGE_METADATA.get(page_key, PAGE_METADATA["404"])
    title = meta["title"]
    description = meta["description"]
    canonical_url = get_canonical_url(page_key)
    og_image_url = get_og_image_url()
    structured_json = json.dumps(get_structured_data(page_key), indent=None)

    # Client-side helper script updating parent document head
    injection_html = f"""
    <div id="ks-seo-marker" data-page="{page_key}" style="display:none;"></div>
    <script>
    (function() {{
        try {{
            var doc = window.parent.document || document;
            
            // 1. Update Title
            doc.title = {json.dumps(title)};

            // Helper to set or create meta tag
            function setMeta(attr, val, content) {{
                var el = doc.querySelector('meta[' + attr + '="' + val + '"]');
                if (!el) {{
                    el = doc.createElement('meta');
                    el.setAttribute(attr, val);
                    doc.head.appendChild(el);
                }}
                el.setAttribute('content', content);
            }}

            // 2. Meta Description
            setMeta('name', 'description', {json.dumps(description)});

            // 3. Canonical Tag
            var canonical = doc.querySelector('link[rel="canonical"]');
            if (!canonical) {{
                canonical = doc.createElement('link');
                canonical.setAttribute('rel', 'canonical');
                doc.head.appendChild(canonical);
            }}
            canonical.setAttribute('href', {json.dumps(canonical_url)});

            // 4. Open Graph Tags
            setMeta('property', 'og:title', {json.dumps(title)});
            setMeta('property', 'og:description', {json.dumps(description)});
            setMeta('property', 'og:type', 'website');
            setMeta('property', 'og:url', {json.dumps(canonical_url)});
            setMeta('property', 'og:image', {json.dumps(og_image_url)});
            setMeta('property', 'og:site_name', {json.dumps(APP_NAME)});

            // 5. Twitter Card Tags
            setMeta('name', 'twitter:card', 'summary_large_image');
            setMeta('name', 'twitter:title', {json.dumps(title)});
            setMeta('name', 'twitter:description', {json.dumps(description)});
            setMeta('name', 'twitter:image', {json.dumps(og_image_url)});

            // 6. JSON-LD Structured Data
            var ldJson = doc.querySelector('#ks-json-ld');
            if (!ldJson) {{
                ldJson = doc.createElement('script');
                ldJson.id = 'ks-json-ld';
                ldJson.type = 'application/ld+json';
                doc.head.appendChild(ldJson);
            }}
            ldJson.textContent = {json.dumps(structured_json)};
        }} catch (e) {{
            // Cross-origin fallback (if embedded in a third-party domain)
        }}
    }})();
    </script>
    """
    st.html(injection_html)
