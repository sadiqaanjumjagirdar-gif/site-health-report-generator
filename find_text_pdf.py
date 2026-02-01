import requests
from bs4 import BeautifulSoup
import pandas as pd
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import fitz  # PyMuPDF
import os

def find_text_in_pdf(keyword):
    sitemap_url = "https://www.micron.com/sitemap.xml"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'
    }

    try:
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
    except requests.RequestException as e:
        return f"Failed to fetch sitemap: {e}", []

    matching_pdfs = []

    for i, url in enumerate(urls):
        try:
            page_response = requests.get(url, headers=headers)
            page_response.raise_for_status()
            soup = BeautifulSoup(page_response.text, 'html.parser')

            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.lower().endswith('.pdf'):
                    pdf_url = urljoin(url, href) if href.startswith('/') else href
                    pdf_response = requests.get(pdf_url, headers=headers)
                    if pdf_response.status_code == 200:
                        temp_pdf = "temp.pdf"
                        with open(temp_pdf, "wb") as f:
                            f.write(pdf_response.content)
                        try:
                            with fitz.open(temp_pdf) as doc:
                                page_texts = []
                                for j in range(doc.page_count):
                                    page = doc.load_page(j)
                                    page_text = page.get_text()
                                    if isinstance(page_text, str):
                                        page_texts.append(page_text)
                                text = "\n".join(page_texts)
                            if keyword.lower() in text.lower():
                                matching_pdfs.append({'PDF File': pdf_url, 'Found Text': keyword})
                        except Exception as e:
                            continue
                        finally:
                            os.remove(temp_pdf)
        except requests.RequestException:
            continue

    excel_filename = f"pdfs_with_{keyword}.xlsx"
    pd.DataFrame(matching_pdfs).to_excel(excel_filename, index=False)

    summary = f"Checked {len(urls)} pages. Found {len(matching_pdfs)} PDFs containing '{keyword}'. See {excel_filename} for details."
    return summary, matching_pdfs