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


def extract_text(path: Path | str) -> str:
    with zipfile.ZipFile(path) as archive:
        content = archive.read("content.xml")
    root = ElementTree.fromstring(content)
    text = " ".join(fragment.strip() for fragment in root.itertext() if fragment.strip())
    return re.sub(r"\s+", " ", text).strip()


def _paragraph_xml(line: str) -> str:
    if line.startswith("## "):
        return f'<text:h text:outline-level="2">{html.escape(line[3:])}</text:h>'
    if line.startswith("- "):
        return f'<text:p text:style-name="List">{html.escape(line)}</text:p>'
    return f"<text:p>{html.escape(line)}</text:p>"
