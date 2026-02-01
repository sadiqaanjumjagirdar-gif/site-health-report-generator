import os
import certifi
from bs4 import BeautifulSoup
import pandas as pd
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

from http_client import get_session


def generate_pdf_link_report():
    """
    Crawl Micron sitemap pages and find broken PDF links.

    Returns:
        summary (str)
        broken_items (list[dict])  # keys: 'Page URL', 'Broken PDF URL', 'Error'

    Notes:
    - Uses HEAD first for speed; falls back to GET when HEAD is blocked.
    - Uses certifi CA bundle for consistent TLS verification.
    - Optionally limits pages scanned with MAX_SITEMAP_PAGES env var to avoid long runs.
    """
    session = get_session()

    sitemap_url = os.getenv("SITEMAP_URL", "https://www.micron.com/sitemap.xml")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36"
        )
    }

    # Optional limit to prevent long runs/timeouts
    try:
        max_pages = int(os.getenv("MAX_SITEMAP_PAGES", "250"))
    except ValueError:
        max_pages = 250

    # Fetch sitemap
    try:
        resp = session.get(sitemap_url, headers=headers, verify=certifi.where(), timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as e:
        return f"Failed to fetch sitemap: {e}", []

    namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = []
    for url_node in root.findall("ns:url", namespace):
        loc_tag = url_node.find("ns:loc", namespace)
        if loc_tag is not None and loc_tag.text:
            urls.append(loc_tag.text.strip())

    if max_pages > 0:
        urls = urls[:max_pages]

    broken_items = []
    pages_checked = 0
    pdfs_checked = 0

    for page_url in urls:
        pages_checked += 1

        # Fetch page HTML
        try:
            page_resp = session.get(page_url, headers=headers, verify=certifi.where(), timeout=30)
            page_resp.raise_for_status()
        except Exception:
            continue

        soup = BeautifulSoup(page_resp.text, "html.parser")

        # Extract PDF links
        for link in soup.find_all("a", href=True):
            href = (link.get("href") or "").strip()
            if not href or not href.lower().endswith(".pdf"):
                continue

            pdf_url = urljoin(page_url, href) if href.startswith("/") else href
            pdfs_checked += 1

            try:
                r = session.head(
                    pdf_url,
                    headers=headers,
                    allow_redirects=True,
                    verify=certifi.where(),
                    timeout=20,
                )
                status = r.status_code

                if status in (403, 405):
                    r = session.get(
                        pdf_url,
                        headers=headers,
                        allow_redirects=True,
                        verify=certifi.where(),
                        timeout=20,
                    )
                    status = r.status_code

                if status >= 400:
                    broken_items.append(
                        {"Page URL": page_url, "Broken PDF URL": pdf_url, "Error": status}
                    )

            except Exception as e:
                broken_items.append(
                    {"Page URL": page_url, "Broken PDF URL": pdf_url, "Error": str(e)}
                )

    # Optional: save local file when running locally
    if os.getenv("SAVE_LOCAL_EXCEL", "0") == "1":
        pd.DataFrame(broken_items).to_excel("broken_pdf_links.xlsx", index=False)

    summary = (
        f"Checked {pages_checked} pages. "
        f"Checked {pdfs_checked} PDF links. "
        f"Broken PDF links found: {len(broken_items)}."
    )
    return summary, broken_items