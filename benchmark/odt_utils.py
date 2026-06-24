from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree


def create_odt(path: Path | str, title: str, paragraphs: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    body = "\n".join(_paragraph_xml(line) for line in paragraphs)
    content_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
  xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
  office:version="1.2">
  <office:automatic-styles/>
  <office:body>
    <office:text>
      <text:h text:outline-level="1">{html.escape(title)}</text:h>
      {body}
    </office:text>
  </office:body>
</office:document-content>
"""
    manifest_xml = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest
  xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
  manifest:version="1.2">
  <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""
    meta_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  office:version="1.2">
  <office:meta>
    <dc:title>{html.escape(title)}</dc:title>
  </office:meta>
</office:document-meta>
"""

    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/vnd.oasis.opendocument.text",
            compress_type=zipfile.ZIP_STORED,
        )
        archive.writestr("content.xml", content_xml)
        archive.writestr("meta.xml", meta_xml)
        archive.writestr("META-INF/manifest.xml", manifest_xml)


def create_review_odt(path: Path | str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    title = "Q3 Revenue Operations Review"
    chart_path = "Pictures/monthly_revenue_margin_chart.svg"

    content_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
  xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
  xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  office:version="1.2">
  <office:body>
    <office:text>
      <text:h text:outline-level="1">{html.escape(title)}</text:h>
      <text:h text:outline-level="2">Executive Summary</text:h>
      <text:p>Q3 revenue operations closed above plan, with expansion revenue offsetting slower new logo conversion in the enterprise segment.</text:p>
      <text:p>Operating focus for Q4 is forecast hygiene, partner pipeline conversion, and faster exception resolution in billing operations.</text:p>
      {_table_xml("KPI Scorecard", [
          ["Metric", "Q3 Actual", "Target", "Status"],
          ["Net Revenue Retention", "118%", "115%", "Ahead"],
          ["Pipeline Coverage", "3.4x", "3.0x", "Ahead"],
          ["Forecast Accuracy", "92%", "90%", "On Track"],
          ["Gross Margin", "74%", "72%", "Ahead"],
      ])}
      {_table_xml("Regional Performance", [
          ["Region", "Revenue", "Pipeline", "Commentary"],
          ["North America", "$18.4M", "$54.2M", "Expansion revenue offset enterprise slippage."],
          ["EMEA", "$9.7M", "$24.5M", "Partner-sourced pipeline improved late in quarter."],
          ["APAC", "$4.1M", "$11.8M", "Execution stable with selective hiring constraints."],
      ])}
      <text:h text:outline-level="2">Monthly Revenue And Margin Trend</text:h>
      <text:p>The chart compares Revenue and Gross Margin for July, August, and September.</text:p>
      <draw:frame draw:name="Monthly Revenue And Margin Trend" text:anchor-type="paragraph" draw:z-index="0" svg:width="16cm" svg:height="8cm" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0">
        <draw:image xlink:href="{chart_path}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/>
      </draw:frame>
      {_table_xml("Strategic Initiatives", [
          ["Initiative", "Owner", "Milestone", "Due"],
          ["Renewal desk automation", "Revenue Operations", "Pilot workflow live", "2026-10-15"],
          ["Partner-sourced pipeline", "Channel Sales", "Top 20 partner plans approved", "2026-10-31"],
          ["Billing exception cleanup", "Data Operations", "Aged backlog under 50 tickets", "2026-11-15"],
      ])}
      {_table_xml("Risk Register", [
          ["Risk", "Impact", "Mitigation"],
          ["Enterprise sales cycle slippage", "Q4 bookings pressure", "Tighten late-stage inspection and executive sponsor mapping."],
          ["Data quality backlog", "Forecast confidence erosion", "Approve two incremental data operations contractors for Q4."],
          ["Partner enablement capacity", "Pipeline conversion risk", "Prioritize partners by sourced opportunity value."],
      ])}
      <text:h text:outline-level="2">Decisions Requested</text:h>
      <text:p>Approve two incremental data operations contractors for Q4.</text:p>
      <text:p>Confirm Q4 operating review cadence and escalation owners by October 4.</text:p>
    </office:text>
  </office:body>
</office:document-content>
"""
    manifest_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest
  xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
  manifest:version="1.2">
  <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="{chart_path}" manifest:media-type="image/svg+xml"/>
</manifest:manifest>
"""
    meta_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  office:version="1.2">
  <office:meta>
    <dc:title>{html.escape(title)}</dc:title>
  </office:meta>
</office:document-meta>
"""

    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/vnd.oasis.opendocument.text",
            compress_type=zipfile.ZIP_STORED,
        )
        archive.writestr("content.xml", content_xml)
        archive.writestr("meta.xml", meta_xml)
        archive.writestr("META-INF/manifest.xml", manifest_xml)
        archive.writestr(chart_path, _chart_svg())


def extract_text(path: Path | str) -> str:
    with zipfile.ZipFile(path) as archive:
        content = archive.read("content.xml")
    root = ElementTree.fromstring(content)
    text = " ".join(fragment.strip() for fragment in root.itertext() if fragment.strip())
    return re.sub(r"\s+", " ", text).strip()


def list_entries(path: Path | str) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return archive.namelist()


def count_content_elements(path: Path | str, element_name: str) -> int:
    with zipfile.ZipFile(path) as archive:
        content = archive.read("content.xml")
    return content.decode("utf-8", errors="replace").count(element_name)


def read_entry_text(path: Path | str, entry_name: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(entry_name).decode("utf-8", errors="replace")


def _paragraph_xml(line: str) -> str:
    if line.startswith("## "):
        return f'<text:h text:outline-level="2">{html.escape(line[3:])}</text:h>'
    if line.startswith("- "):
        return f'<text:p text:style-name="List">{html.escape(line)}</text:p>'
    return f"<text:p>{html.escape(line)}</text:p>"


def _table_xml(name: str, rows: list[list[str]]) -> str:
    row_xml = []
    for row in rows:
        cells = "".join(
            f"<table:table-cell><text:p>{html.escape(cell)}</text:p></table:table-cell>"
            for cell in row
        )
        row_xml.append(f"<table:table-row>{cells}</table:table-row>")
    return (
        f'<text:h text:outline-level="2">{html.escape(name)}</text:h>'
        f'<table:table table:name="{html.escape(name)}">'
        f'{"".join(row_xml)}'
        "</table:table>"
    )


def _chart_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420">
  <rect width="900" height="420" fill="#ffffff"/>
  <text x="40" y="42" font-family="Arial" font-size="26" font-weight="700">Monthly Revenue And Margin Trend</text>
  <line x1="80" y1="340" x2="820" y2="340" stroke="#333" stroke-width="2"/>
  <line x1="80" y1="80" x2="80" y2="340" stroke="#333" stroke-width="2"/>
  <text x="145" y="375" font-family="Arial" font-size="18">July</text>
  <text x="390" y="375" font-family="Arial" font-size="18">August</text>
  <text x="635" y="375" font-family="Arial" font-size="18">September</text>
  <rect x="130" y="170" width="60" height="170" fill="#2f6f8f"/>
  <rect x="380" y="135" width="60" height="205" fill="#2f6f8f"/>
  <rect x="630" y="105" width="60" height="235" fill="#2f6f8f"/>
  <rect x="200" y="235" width="60" height="105" fill="#5aa469"/>
  <rect x="450" y="218" width="60" height="122" fill="#5aa469"/>
  <rect x="700" y="198" width="60" height="142" fill="#5aa469"/>
  <text x="130" y="160" font-family="Arial" font-size="16">$9.8M</text>
  <text x="380" y="125" font-family="Arial" font-size="16">$10.7M</text>
  <text x="630" y="95" font-family="Arial" font-size="16">$11.7M</text>
  <text x="200" y="225" font-family="Arial" font-size="16">72%</text>
  <text x="450" y="208" font-family="Arial" font-size="16">73%</text>
  <text x="700" y="188" font-family="Arial" font-size="16">74%</text>
  <rect x="610" y="28" width="24" height="16" fill="#2f6f8f"/>
  <text x="644" y="42" font-family="Arial" font-size="16">Revenue</text>
  <rect x="720" y="28" width="24" height="16" fill="#5aa469"/>
  <text x="754" y="42" font-family="Arial" font-size="16">Gross Margin</text>
</svg>
"""
