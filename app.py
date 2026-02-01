# app.py
from flask import Flask, request, send_file, render_template
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from typing import cast
from io import BytesIO

# Import your report generator functions
import broken_link
import header
import footer
import image_link
import metadata_link
import pdf_link
import find_text
import find_text_pdf

# ✅ New import
import asset_404

app = Flask(__name__)


def generate_reports(selected_reports, find_text_url, find_text_pdf_keyword, asset_urls):
    report_data = []
    # Each tuple: (report_type, summary, details_list, details_headers)

    if 'broken-link' in selected_reports:
        summary, details = broken_link.generate_broken_link_report()
        headers = ['Page URL', 'Broken Link', 'Error']
        report_data.append(('Broken Link', summary, details, headers))

    if 'header' in selected_reports:
        summary, details = header.generate_header_nav_report()
        headers = ['Country', 'Link URL', 'Link Text', 'Status Code', 'Error']
        report_data.append(('Header Navigation', summary, details, headers))

    if 'footer' in selected_reports:
        summary, details = footer.generate_footer_nav_report()
        headers = ['Country', 'Link URL', 'Link Text', 'Status Code', 'Error']
        report_data.append(('Footer Navigation', summary, details, headers))

    if 'image' in selected_reports:
        summary, details = image_link.generate_image_link_report()
        headers = ['Page URL', 'Broken Image URL', 'Error']
        report_data.append(('Image Links', summary, details, headers))

    if 'metadata' in selected_reports:
        summary, details = metadata_link.generate_metadata_report()
        headers = [
            'URL', 'Title Tag', 'Meta Description', 'Meta Keywords',
            'Title Tag Character Count', 'Meta Description Character Count', 'Meta Keywords Character Count'
        ]
        report_data.append(('Metadata', summary, details, headers))

    if 'pdf' in selected_reports:
        summary, details = pdf_link.generate_pdf_link_report()
        headers = ['Page URL', 'Broken PDF URL', 'Error']
        report_data.append(('PDF Links', summary, details, headers))

    if 'find-text-url' in selected_reports and find_text_url:
        summary, details = find_text.find_text_in_url(find_text_url)
        headers = ['URL']
        report_data.append(('Find Text in URL', summary, details, headers))

    if 'find-text-pdf' in selected_reports and find_text_pdf_keyword:
        summary, details = find_text_pdf.find_text_in_pdf(find_text_pdf_keyword)
        headers = ['PDF File', 'Found Text']
        report_data.append(('Find Text in PDF', summary, details, headers))

    # ✅ New Advanced option: asset 404 checker
    if 'asset-404' in selected_reports and asset_urls:
        summary, details = asset_404.generate_asset_404_report(asset_urls)
        headers = ['Input Page', 'Asset Type', 'Asset URL', 'Status Code', 'Error']
        report_data.append(('Asset 404 (Links/Images/PDF)', summary, details, headers))

    return report_data


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        selected_reports = request.form.getlist('report')

        find_text_url = request.form.get('find_text_url', '').strip()
        find_text_pdf_keyword = request.form.get('find_text_pdf', '').strip()

        # ✅ New textbox input for URLs
        asset_urls = request.form.get('asset_urls', '').strip()

        if not selected_reports:
            return "Please select at least one report.", 400

        # Create Excel in memory
        output = BytesIO()
        wb = Workbook()
        ws = cast(Worksheet, wb.active)
        ws.title = "Report Summary"
        ws.append(["Report Type", "Details"])

        report_data = generate_reports(selected_reports, find_text_url, find_text_pdf_keyword, asset_urls)

        for report_type, summary, details, headers in report_data:
            ws.append([report_type, summary])

            if details:
                # Add a blank row for spacing
                ws.append(['', ''])

                # Add header row for details
                ws.append(headers)

                # Add each detail row
                for row in details:
                    # If row is a dict, get values in header order
                    if isinstance(row, dict):
                        ws.append([row.get(h, '') for h in headers])
                    else:
                        ws.append(row)

                # Add a blank row after details
                ws.append(['', ''])

        wb.save(output)
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name='site_report.xlsx',  # ✅ consistent name
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)