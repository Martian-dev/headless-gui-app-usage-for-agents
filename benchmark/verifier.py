from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odt_utils import extract_text


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
    return VerifyResult(not missing, missing)


def _search_text(item: str) -> str:
    if item.startswith("## "):
        return item[3:]
    return item
