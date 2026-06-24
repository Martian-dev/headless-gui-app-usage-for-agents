from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from codex_agent import codex_log_tail, run_codex_agent
from odt_utils import create_odt
from verifier import verify


def run_task(task_path: Path, mode: str, workdir: Path) -> dict[str, Any]:
    task = load_task(task_path)
    workdir.mkdir(parents=True, exist_ok=True)
    _reset_workdir(workdir)

    steps = 0
    if mode == "shell-baseline":
        steps = _shell_baseline(task, workdir)
    elif mode == "codex-agent":
        steps = run_codex_agent(task, workdir, workdir / "agent_logs")
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    result = verify(task, workdir / task["expected"]["output_file"])
    payload = {
        "task": task["id"],
        "success": result.success,
        "score": 1 if result.success else 0,
        "steps": steps,
        "missing": result.missing,
        "output_file": str(workdir / task["expected"]["output_file"]),
    }
    if mode == "codex-agent" and not result.success:
        payload["codex_log_tail"] = codex_log_tail(workdir / "agent_logs")
        payload["workdir_files"] = sorted(path.name for path in workdir.iterdir())
    return payload


def load_task(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return _load_known_task_without_yaml(path)

    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _shell_baseline(task: dict[str, Any], workdir: Path) -> int:
    expected = task["expected"]
    create_odt(
        workdir / expected["output_file"],
        expected["title"],
        expected["required_text"],
    )
    return 1


def _reset_workdir(workdir: Path) -> None:
    for child in workdir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    create_odt(workdir / "starter.odt", "Untitled Handoff", ["Replace this starter text."])


def _load_known_task_without_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if "writer_doc_001" not in text:
        raise RuntimeError("PyYAML is not installed and fallback only supports task001.yaml")
    return {
        "id": "writer_doc_001",
        "instruction": (
            "Open the starter document and turn it into a concise operations handoff "
            "for the nightly data refresh."
        ),
        "setup": ["starter.odt"],
        "expected": {
            "output_file": "output.odt",
            "title": "Nightly Data Refresh Handoff",
            "required_text": [
                "## Purpose",
                "Document the owner, schedule, validation checks, and escalation path for the nightly data refresh.",
                "## Schedule",
                "- Runs every weekday at 02:00 UTC.",
                "- Expected completion is before 03:15 UTC.",
                "## Validation Checklist",
                "- Confirm the dashboard row count is within 5% of the previous successful run.",
                "- Confirm no critical errors appear in refresh.log.",
                "- Confirm the success marker file exists before sending the handoff.",
                "## Escalation",
                "If validation fails, notify Data Operations and include the failing check, timestamp, and log excerpt.",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--mode", choices=["shell-baseline", "codex-agent"], default="shell-baseline")
    parser.add_argument("--workdir", default="/workspace/run")
    args = parser.parse_args()

    result = run_task(Path(args.task), args.mode, Path(args.workdir))
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
