# metadata.py

def generate_metadata_report():
    import requests
    from bs4 import BeautifulSoup
    import pandas as pd
    import xml.etree.ElementTree as ET

    sitemap_url = "https://www.micron.com/sitemap.xml"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'
    }
    try:
        response = requests.get(sitemap_url, headers=headers, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        urls = [elem.text for elem in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if elem.text]
    except requests.RequestException as e:
        return f"Failed to fetch sitemap: {e}"

    data = []
    for i, url in enumerate(urls):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            title_tag = soup.find('title')
            title = title_tag.text.strip() if title_tag and title_tag.text else ''
            description_tag = soup.find('meta', {'name': 'description'})
            description = description_tag.get('content', '').strip() if description_tag else ''
            keywords_tag = soup.find('meta', {'name': 'keywords'})
            keywords = keywords_tag.get('content', '').strip() if keywords_tag else ''
            if not title or not description or not keywords:
                data.append([url, title, description, keywords, len(title), len(description), len(keywords)])
        except requests.RequestException as e:
            data.append([url, '', '', '', 0, 0, 0])

    df = pd.DataFrame(data, columns=[
        'URL', 'Title Tag', 'Meta Description', 'Meta Keywords',
        'Title Tag Character Count', 'Meta Description Character Count', 'Meta Keywords Character Count'
    ])
    excel_filename = "micron_empty_metadata_report.xlsx"
    df.to_excel(excel_filename, index=False)
    #return f"Checked {len(urls)} pages. Pages with empty metadata: {len(data)}. See {excel_filename} for details."

    
    summary = f"Checked {len(urls)} pages. Pages with empty metadata: {len(data)}. See {excel_filename} for details."
    return summary, data