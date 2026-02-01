import requests
from bs4 import BeautifulSoup, Tag
import pandas as pd
from urllib.parse import urljoin

def generate_footer_nav_report():
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

    # ✅ 7 locales with labels
    sites = [
        ("EN", "https://www.micron.com/"),
        ("TW",     "https://tw.micron.com/"),
        ("CN",     "https://cn.micron.com"),
        ("SG",     "https://sg.micron.com/"),
        ("MY",     "https://my.micron.com/"),
        ("IN",     "https://in.micron.com/"),
        ("JP",     "https://jp.micron.com/"),  
    ]

    all_rows = []
    broken_rows = []

    for country, page_url in sites:
        # Fetch locale homepage
        try:
            resp = requests.get(page_url, headers=headers, proxies=proxies, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            row = {
                "Country": country,
                "Page URL": page_url,
                "Link Text": "(homepage)",
                "Link URL": page_url,
                "Status Code": "",
                "Error": f"Failed to fetch homepage: {e}",
            }
            broken_rows.append(row)
            all_rows.append(row)
            continue

        footer = soup.find("footer")
        links = footer.find_all("a", href=True) if isinstance(footer, Tag) else []

        for a in links:
            href = (a.get("href") or "").strip()
            text = a.get_text(strip=True)

            # Skip non-links
            if not href or href.startswith("#") or href.lower().startswith(("javascript:", "mailto:", "tel:")):
                continue

            # Resolve relative links per locale
            link_url = urljoin(page_url if page_url.endswith("/") else page_url + "/", href)

            status_code = ""
            error = ""

            try:
                # HEAD first for speed; fallback to GET if blocked
                r = requests.head(
                    link_url,
                    headers=headers,
                    proxies=proxies,
                    allow_redirects=True,
                    timeout=15
                )
                status_code = r.status_code

                if status_code in (403, 405):  # HEAD blocked
                    r = requests.get(
                        link_url,
                        headers=headers,
                        proxies=proxies,
                        allow_redirects=True,
                        timeout=15
                    )
                    status_code = r.status_code

            except requests.RequestException as e:
                error = str(e)

            row = {
                "Country": country,
                "Page URL": page_url,
                "Link Text": text,
                "Link URL": link_url,
                "Status Code": status_code,
                "Error": error
            }

            all_rows.append(row)

            # Broken = request error OR HTTP >= 400
            if error or (isinstance(status_code, int) and status_code >= 400):
                broken_rows.append(row)

    excel_filename = "micron_footer_links_report_7_sites.xlsx"
    with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
        pd.DataFrame(all_rows).to_excel(writer, sheet_name="All Links", index=False)
        pd.DataFrame(broken_rows).to_excel(writer, sheet_name="Broken Links", index=False)

    summary = (
        f"Footer checked for {len(sites)} locales. "
        f"Total links: {len(all_rows)}. Broken: {len(broken_rows)}. "
        f"Saved: {excel_filename}"
    )

    return summary, broken_rows