from flask import Flask, request, send_file, render_template
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from typing import cast, Any
from io import BytesIO

# Import report generator modules
import broken_link
import header
import footer
import image_link
import metadata_link
import pdf_link
import find_text
import find_text_pdf
import asset_404

app = Flask(__name__)


def _safe_append_row(ws: Worksheet, row: Any, headers: list[str] | None = None) -> None:
    """
    Append a row to an openpyxl worksheet safely.

    Supports:
    - dict: values pulled in header order
    - list/tuple: appended as-is (optionally padded/trimmed to headers length)
    - scalar: written into a single cell

    This prevents crashes when a report returns list-of-lists.
    """
    if isinstance(row, dict):
        if not headers:
            for k, v in row.items():
                ws.append([k, v])
            return
        ws.append([row.get(h, "") for h in headers])
        return

    if isinstance(row, (list, tuple)):
        vals = list(row)
        if headers:
            if len(vals) < len(headers):
                vals += [""] * (len(headers) - len(vals))
            elif len(vals) > len(headers):
                vals = vals[: len(headers)]
        ws.append(vals)
        return

    ws.append([row])


def generate_reports(selected_reports: list[str], form: dict[str, str]):
    """
    Run selected report generators and return structured output.

    Each item:
      (report_type, summary, details, headers)

    details can be:
      list[dict] OR list[list] OR list[str]
    """
    report_data = []

    find_text_url = (form.get("find_text_url") or form.get("find_text_url_keyword") or "").strip()
    find_text_pdf_keyword = (form.get("find_text_pdf") or form.get("find_text_pdf_keyword") or "").strip()

    # Asset 404 input name flexibility
    asset_404_urls = (
        form.get("asset_404_urls")
        or form.get("asset_urls")
        or form.get("asset_404")
        or form.get("urls")
        or ""
    ).strip()

    if "broken-link" in selected_reports:
        summary, details = broken_link.generate_broken_link_report()
        headers = ["Page URL", "Broken Link", "Error"]
        report_data.append(("Broken Link", summary, details, headers))

    if "header" in selected_reports:
        summary, details = header.generate_header_nav_report()
        headers = ["Country", "Page URL", "Link Text", "Link URL", "Status Code", "Error"]
        report_data.append(("Header Navigation", summary, details, headers))

    if "footer" in selected_reports:
        summary, details = footer.generate_footer_nav_report()
        headers = ["Country", "Page URL", "Link Text", "Link URL", "Status Code", "Error"]
        report_data.append(("Footer Navigation", summary, details, headers))

    if "image" in selected_reports:
        summary, details = image_link.generate_image_link_report()
        headers = ["Page URL", "Broken Image URL", "Error"]
        report_data.append(("Image Links", summary, details, headers))

    if "metadata" in selected_reports:
        summary, details = metadata_link.generate_metadata_report()
        headers = [
            "URL", "Title Tag", "Meta Description", "Meta Keywords",
            "Title Tag Character Count", "Meta Description Character Count", "Meta Keywords Character Count"
        ]
        report_data.append(("Metadata", summary, details, headers))

    if "pdf" in selected_reports:
        summary, details = pdf_link.generate_pdf_link_report()
        headers = ["Page URL", "Broken PDF URL", "Error"]
        report_data.append(("PDF Links", summary, details, headers))

    if "find-text-url" in selected_reports and find_text_url:
        summary, details = find_text.find_text_in_url(find_text_url)
        headers = ["URL"]
        report_data.append(("Find Text in URL", summary, details, headers))

    if "find-text-pdf" in selected_reports and find_text_pdf_keyword:
        summary, details = find_text_pdf.find_text_in_pdf(find_text_pdf_keyword)
        headers = ["PDF File", "Found Text"]
        report_data.append(("Find Text in PDF", summary, details, headers))

    if "asset-404" in selected_reports:
        if not asset_404_urls:
            summary, details = "No URLs provided for Asset 404 check.", []
        else:
            summary, details = asset_404.generate_asset_404_report(asset_404_urls)

        headers = ["Input Page", "Asset Type", "Asset URL", "Status Code", "Error"]
        report_data.append(("Asset 404", summary, details, headers))

    return report_data


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        selected_reports = request.form.getlist("report")
        if not selected_reports:
            return "Please select at least one report.", 400

        form_data = {k: v for k, v in request.form.items()}

        output = BytesIO()
        wb = Workbook()
        ws = cast(Worksheet, wb.active)
        ws.title = "Report Summary"
        ws.append(["Report Type", "Details"])

        try:
            report_data = generate_reports(selected_reports, form_data)

            for report_type, summary, details, headers in report_data:
                ws.append([report_type, summary])

                if details:
                    ws.append(["", ""])  # spacer
                    ws.append(headers)

                    for row in details:
                        _safe_append_row(ws, row, headers=headers)

                    ws.append(["", ""])  # spacer

        except Exception as e:
            return f"Internal Server Error: {e}", 500

        wb.save(output)
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name="site_health_report.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    return render_template("index.html")


@app.get("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(debug=True)