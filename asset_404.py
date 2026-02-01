# asset_404.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import certifi

MAX_INPUT_URLS = 20  # ✅ Only 20 URLs allowed at a time (comma-separated or newline-separated)


def _normalize_input_urls(raw: str):
    """
    Accepts URLs separated by newlines OR commas.
    Adds https:// if missing.
    Max 20 enforced in generate_asset_404_report().
    """
    if not raw:
        return []

    urls = []
    # Support comma-separated and newline-separated
    for chunk in raw.replace(",", "\n").splitlines():
        u = chunk.strip()
        if not u:
            continue
        if u.startswith("www."):
            u = "https://" + u
        if not u.startswith(("http://", "https://")):
            u = "https://" + u
        urls.append(u)

    # De-duplicate while preserving order
    seen = set()
    deduped = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


def _extract_srcset_urls(srcset: str):
    """
    Parse srcset="url1 1x, url2 2x" -> ["url1", "url2"]
    """
    if not srcset:
        return []
    out = []
    for part in srcset.split(","):
        part = part.strip()
        if not part:
            continue
        url = part.split()[0].strip()
        if url:
            out.append(url)
    return out


def _is_pdf(url: str):
    try:
        return urlparse(url).path.lower().endswith(".pdf")
    except Exception:
        return url.lower().endswith(".pdf")


def _is_image(url: str):
    url_l = url.lower()
    return any(url_l.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif"])


def _check_url_status(url: str, headers, proxies, timeout=15):
    """
    HEAD first for speed; fallback to GET for 403/405 or HEAD failures.
    Returns (status_code:int|None, error:str).
    """
    try:
        r = requests.head(
            url,
            headers=headers,
            proxies=proxies,
            allow_redirects=True,
            verify=certifi.where(),
            timeout=timeout
        )
        status = r.status_code

        # Some servers block HEAD
        if status in (403, 405):
            r = requests.get(
                url,
                headers=headers,
                proxies=proxies,
                allow_redirects=True,
                verify=certifi.where(),
                timeout=timeout
            )
            status = r.status_code

        return status, ""
    except requests.RequestException as e:
        # Try GET once if HEAD failed
        try:
            r = requests.get(
                url,
                headers=headers,
                proxies=proxies,
                allow_redirects=True,
                verify=certifi.where(),
                timeout=timeout
            )
            return r.status_code, ""
        except requests.RequestException as e2:
            return None, str(e2)


def generate_asset_404_report(raw_urls: str):
    """
    User provides up to 20 URLs (comma-separated or one per line).
    For each page:
      - extract all links (<a href>), images (<img src/srcset>, <source srcset>), and PDFs
      - check each extracted asset
      - return ONLY assets that respond with HTTP 404 (one row per 404)
    """
    proxies = {
        "http": "http://proxy-web.micron.com:80",
        "https": "http://proxy-web.micron.com:80",
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36"
        )
    }

    page_urls = _normalize_input_urls(raw_urls)

    if not page_urls:
        return "No URLs provided for Asset 404 check.", []

    if len(page_urls) > MAX_INPUT_URLS:
        return f"Please provide up to {MAX_INPUT_URLS} URLs only (you entered {len(page_urls)}).", []

    broken_404 = []
    pages_checked = 0
    assets_checked = 0

    for page_url in page_urls:
        pages_checked += 1

        # Fetch the page HTML
        try:
            resp = requests.get(
                page_url,
                headers=headers,
                proxies=proxies,
                allow_redirects=True,
                verify=certifi.where(),
                timeout=20
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            # If the page itself fails, log an informational row (not necessarily 404 assets)
            broken_404.append({
                "Input Page": page_url,
                "Asset Type": "PAGE",
                "Asset URL": page_url,
                "Status Code": getattr(getattr(e, "response", None), "status_code", ""),
                "Error": f"Failed to fetch page: {e}"
            })
            continue

        # Collect assets (dedupe per page for speed)
        assets = set()

        # --- Links (<a href>) ---
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            if href.startswith("#") or href.lower().startswith(("javascript:", "mailto:", "tel:")):
                continue
            assets.add(urljoin(page_url, href))

        # --- Images (<img src/data-src>) + srcset ---
        for img in soup.find_all("img"):
            src = (img.get("src") or img.get("data-src") or "").strip()
            if src:
                assets.add(urljoin(page_url, src))

            srcset = (img.get("srcset") or img.get("data-srcset") or "").strip()
            for u in _extract_srcset_urls(srcset):
                assets.add(urljoin(page_url, u))

        # <source srcset> (for responsive images/videos)
        for source in soup.find_all("source"):
            srcset = (source.get("srcset") or "").strip()
            for u in _extract_srcset_urls(srcset):
                assets.add(urljoin(page_url, u))

        # Check each asset; store ONLY 404 rows
        for asset_url in sorted(assets):
            assets_checked += 1
            status, err = _check_url_status(asset_url, headers=headers, proxies=proxies)

            if status == 404:
                if _is_pdf(asset_url):
                    asset_type = "PDF"
                elif _is_image(asset_url):
                    asset_type = "Image"
                else:
                    asset_type = "Link"

                broken_404.append({
                    "Input Page": page_url,
                    "Asset Type": asset_type,
                    "Asset URL": asset_url,
                    "Status Code": status,
                    "Error": err
                })

    summary = (
        f"Asset 404 check completed. Pages checked: {pages_checked}. "
        f"Assets checked: {assets_checked}. 404 assets found: {len(broken_404)}."
    )
    return summary, broken_404