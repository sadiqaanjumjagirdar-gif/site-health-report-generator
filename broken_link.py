import requests
import pandas as pd
import xml.etree.ElementTree as ET
import certifi

def generate_broken_link_report():
    sitemap_url = "https://www.micron.com/sitemap.xml"
    headers = {"User-Agent": "Mozilla/5.0"}

    # --- Fetch sitemap ---
    try:
        response = requests.get(
            sitemap_url,
            headers=headers,
            verify=certifi.where(),
            timeout=20
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
    except requests.RequestException as e:
        return f"Error fetching sitemap: {e}"
    except ET.ParseError as e:
        return f"Error parsing sitemap XML: {e}"

    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    # --- Extract URLs from sitemap ---
    urls = []
    for url_node in root.findall('ns:url', namespace):
        loc_tag = url_node.find('ns:loc', namespace)
        if loc_tag is not None and loc_tag.text:
            urls.append(loc_tag.text.strip())

    broken_links = []

    # --- Check ONLY the sitemap URLs ---
    for page_url in urls:
        try:
            # Prefer HEAD for speed; fall back to GET if blocked
            try:
                r = requests.head(
                    page_url,
                    headers=headers,
                    allow_redirects=True,
                    verify=certifi.where(),
                    timeout=20
                )
                status = r.status_code

                # Some sites return 405/403 to HEAD; retry with GET
                if status in (403, 405):
                    r = requests.get(
                        page_url,
                        headers=headers,
                        allow_redirects=True,
                        verify=certifi.where(),
                        timeout=20
                    )
                    status = r.status_code

            except requests.RequestException:
                # If HEAD fails, try GET once
                r = requests.get(
                    page_url,
                    headers=headers,
                    allow_redirects=True,
                    verify=certifi.where(),
                    timeout=20
                )
                status = r.status_code

            if status >= 400:
                broken_links.append([page_url, status, "HTTP error"])

        except requests.RequestException as e:
            broken_links.append([page_url, "", str(e)])

    # --- Save to Excel ---
    broken_df = pd.DataFrame(broken_links, columns=['Sitemap URL', 'Status Code', 'Error'])
    excel_filename = "broken_links.xlsx"
    broken_df.to_excel(excel_filename, index=False)

    summary = (
        f"Checked {len(urls)} sitemap URLs. "
        f"Found {len(broken_links)} broken sitemap URLs. "
        f"See {excel_filename} for details."
    )
    return summary, broken_links