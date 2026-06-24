from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odt_utils import count_content_elements, extract_text, list_entries, read_entry_text


@dataclass(frozen=True)
class VerifyResult:
    success: bool
    missing: list[str]


def verify(task: dict[str, Any], output_path: Path) -> VerifyResult:
    if not output_path.exists():
        return VerifyResult(False, [f"missing artifact: {output_path.name}"])

    expected = task["expected"]
    text = extract_text(output_path)
    required = [expected["title"], *expected["required_text"]]
    missing = [item for item in required if _search_text(item) not in text]

    entries = list_entries(output_path)
    for chart_path in expected.get("required_chart_images", []):
        if chart_path not in entries:
            missing.append(f"missing chart image: {chart_path}")

    min_tables = expected.get("min_tables")
    if min_tables is not None:
        table_count = count_content_elements(output_path, "<table:table ")
        if table_count < min_tables:
            missing.append(f"expected at least {min_tables} tables, found {table_count}")

    min_chart_images = expected.get("min_chart_images")
    if min_chart_images is not None:
        chart_count = sum(
            1 for entry in entries if entry.startswith("Pictures/") and entry.endswith(".svg")
        )
        if chart_count < min_chart_images:
            missing.append(f"expected at least {min_chart_images} chart images, found {chart_count}")

    for table_name in expected.get("required_tables", []):
        if table_name not in text:
            missing.append(f"missing table: {table_name}")

    chart_text = " ".join(
        read_entry_text(output_path, entry)
        for entry in entries
        if entry.startswith("Pictures/") and entry.endswith(".svg")
    )
    for label in expected.get("required_chart_labels", []):
        if label not in chart_text and label not in text:
            missing.append(f"missing chart label: {label}")

    return VerifyResult(not missing, missing)


def _search_text(item: str) -> str:
    if item.startswith("## "):
        return item[3:]
    return item
