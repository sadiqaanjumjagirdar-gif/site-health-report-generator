import requests
from bs4 import BeautifulSoup
import pandas as pd
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

def generate_image_link_report():
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
        if loc_tag is not None and loc_tag.text and "part-detail" not in loc_tag.text:
            urls.append(loc_tag.text)

    broken_images = []
    for url in urls:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for img in soup.find_all('img', src=True):
                src = img['src']
                if src.startswith('/'):
                    src = urljoin(url, src)
                try:
                    img_response = requests.head(src, headers=headers, allow_redirects=True)
                    if img_response.status_code >= 400:
                        broken_images.append([url, src, img_response.status_code])
                except requests.RequestException as e:
                    broken_images.append([url, src, str(e)])
        except requests.RequestException as e:
            continue

    broken_df = pd.DataFrame(broken_images, columns=['Page URL', 'Broken Image URL', 'Error'])
    excel_filename = "broken_image_links.xlsx"
    broken_df.to_excel(excel_filename, index=False)
    #return f"Checked {len(urls)} pages. Found {len(broken_images)} broken images. See {excel_filename} for details."
    
    
    summary = f"Checked {len(urls)} pages. Found {len(broken_images)} broken images. See {excel_filename} for details."
    # Return summary and details (all broken images)
    return summary, broken_images