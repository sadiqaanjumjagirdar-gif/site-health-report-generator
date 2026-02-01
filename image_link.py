import os
import certifi
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from http_client import get_session


def generate_image_link_report():
    """
    Crawl Micron sitemap pages and find broken image links.

    Returns:
        summary (str)
        broken_items (list[dict])  # keys: 'Page URL', 'Broken Image URL', 'Error'
    """

    session = get_session()

    sitemap_url = os.getenv("SITEMAP_URL", "https://www.micron.com/sitemap.xml")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36"
        )
    }

    # Optional limit to avoid long runs on Render
    # Set MAX_SITEMAP_PAGES=0 to scan all
    try:
        max_pages = int(os.getenv("MAX_SITEMAP_PAGES", "250"))
    except ValueError:
        max_pages = 250

    # Fetch sitemap safely
    try:
        resp = session.get(
            sitemap_url,
            headers=headers,
            verify=certifi.where(),
            timeout=30
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as e:
        return f"Failed to fetch sitemap: {e}", []

    namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = []

    for url_node in root.findall("ns:url", namespace):
        loc_tag = url_node.find("ns:loc", namespace)
        if loc_tag is not None and loc_tag.text:
            loc = loc_tag.text.strip()
            if "part-detail" not in loc:
                urls.append(loc)

    if max_pages > 0:
        urls = urls[:max_pages]

    broken_items = []
    pages_checked = 0
    images_checked = 0

    for page_url in urls:
        pages_checked += 1

        # Fetch page HTML
        try:
            page_resp = session.get(
                page_url,
                headers=headers,
                verify=certifi.where(),
                timeout=30
            )
            page_resp.raise_for_status()
        except Exception:
            # Skip page failures; report focuses on broken images
            continue

        soup = BeautifulSoup(page_resp.text, "html.parser")

        for img in soup.find_all("img", src=True):
            src = (img.get("src") or "").strip()
            if not src:
                continue

            img_url = urljoin(page_url, src) if src.startswith("/") else src
            images_checked += 1

            try:
                r = session.head(
                    img_url,
                    headers=headers,
                    allow_redirects=True,
                    verify=certifi.where(),
                    timeout=20
                )
                status = r.status_code

                # Some servers block HEAD
                if status in (403, 405):
                    r = session.get(
                        img_url,
                        headers=headers,
                        allow_redirects=True,
                        verify=certifi.where(),
                        timeout=20
                    )
                    status = r.status_code

                if status >= 400:
                    broken_items.append({
                        "Page URL": page_url,
                        "Broken Image URL": img_url,
                        "Error": status
                    })

            except Exception as e:
                broken_items.append({
                    "Page URL": page_url,
                    "Broken Image URL": img_url,
                    "Error": str(e)
                })

    summary = (
        f"Checked {pages_checked} pages. "
        f"Checked {images_checked} images. "
        f"Broken images found: {len(broken_items)}."
    )
    return summary, broken_items