# metadata_link.py
import os
import certifi
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from http_client import get_session


def generate_metadata_report():
    """
    Checks pages from the sitemap for missing metadata fields:
    - <title>
    - meta[name="description"]
    - meta[name="keywords"]

    Returns:
        summary (str)
        details (list[list])  # rows matching headers in app.py
    """

    session = get_session()

    sitemap_url = os.getenv("SITEMAP_URL", "https://www.micron.com/sitemap.xml")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36"
        )
    }

    # Optional limit to prevent long runtime on Render
    # Set MAX_SITEMAP_PAGES=0 to scan all pages
    try:
        max_pages = int(os.getenv("MAX_SITEMAP_PAGES", "250"))
    except ValueError:
        max_pages = 250

    # Fetch sitemap
    try:
        response = session.get(
            sitemap_url,
            headers=headers,
            verify=certifi.where(),
            timeout=30
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)

        urls = [
            elem.text.strip()
            for elem in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            if elem.text
        ]

        if max_pages > 0:
            urls = urls[:max_pages]

    except Exception as e:
        # ✅ Always return a tuple to avoid app.py unpacking crash
        return f"Failed to fetch sitemap: {e}", []

    data = []

    for url in urls:
        try:
            res = session.get(url, headers=headers, verify=certifi.where(), timeout=20)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            title_tag = soup.find("title")
            title = title_tag.text.strip() if title_tag and title_tag.text else ""

            description_tag = soup.find("meta", {"name": "description"})
            description = description_tag.get("content", "").strip() if description_tag else ""

            keywords_tag = soup.find("meta", {"name": "keywords"})
            keywords = keywords_tag.get("content", "").strip() if keywords_tag else ""

            # record only if anything is missing
            if not title or not description or not keywords:
                data.append([
                    url,
                    title,
                    description,
                    keywords,
                    len(title),
                    len(description),
                    len(keywords)
                ])

        except Exception:
            # Keep a row so the report shows it was not reachable
            data.append([url, "", "", "", 0, 0, 0])

    # Optional local save (useful on your machine, not needed on Render)
    if os.getenv("SAVE_LOCAL_EXCEL", "0") == "1":
        df = pd.DataFrame(
            data,
            columns=[
                "URL", "Title Tag", "Meta Description", "Meta Keywords",
                "Title Tag Character Count", "Meta Description Character Count", "Meta Keywords Character Count"
            ]
        )
        df.to_excel("micron_empty_metadata_report.xlsx", index=False)

    summary = (
        f"Checked {len(urls)} pages. Pages with empty metadata: {len(data)}."
    )
    return summary, data