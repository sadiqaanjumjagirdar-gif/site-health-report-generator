import requests
from bs4 import BeautifulSoup
import pandas as pd
import xml.etree.ElementTree as ET


def find_text_in_url(keyword):
    sitemap_url = "https://www.micron.com/sitemap.xml"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'
    }
    response = requests.get(sitemap_url, headers=headers)
    response.raise_for_status()
    sitemap_xml = response.text
    root = ET.fromstring(sitemap_xml)
    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = []
    for url in root.findall('ns:url', namespace):
        loc_tag = url.find('ns:loc', namespace)
        if loc_tag is not None and loc_tag.text:
            urls.append(loc_tag.text)

    found_urls = []
    for url in urls:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            visible_text = soup.get_text(separator=' ', strip=True)
            if keyword.lower() in visible_text.lower():
                found_urls.append(url)
        except requests.RequestException:
            continue

    # THIS IS THE FIX:
    output_df = pd.DataFrame(found_urls, columns=['URL'])
    # Alternative safe way:
    # output_df = pd.DataFrame([[url] for url in found_urls], columns=['URL'])

    excel_filename = f"output_{keyword}_search.xlsx"
    output_df.to_excel(excel_filename, index=False)

    summary = f"Keyword '{keyword}' found in {len(found_urls)} pages. See {excel_filename} for details."
    return summary, found_urls
