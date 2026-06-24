from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from codex_agent import codex_log_tail, run_codex_agent
from env import Environment
from odt_utils import create_odt, create_review_odt
from openrouter_gui_agent import openrouter_log_tail, run_openrouter_gui_agent
from verifier import verify


def run_task(task_path: Path, mode: str, workdir: Path) -> dict[str, Any]:
    task = load_task(task_path)
    workdir.mkdir(parents=True, exist_ok=True)
    _reset_workdir(workdir)

    steps = 0
    if mode == "shell-baseline":
        steps = _shell_baseline(task, workdir)
    elif mode in {"codex-agent", "openrouter-gui-agent"}:
        gui = Environment(workdir)
        try:
            gui.start_gui(workdir / "starter.odt")
            if mode == "codex-agent":
                steps = run_codex_agent(task, workdir, workdir / "agent_logs")
            else:
                try:
                    steps = run_openrouter_gui_agent(task, workdir, workdir / "agent_logs")
                except RuntimeError as exc:
                    (workdir / "agent_logs").mkdir(parents=True, exist_ok=True)
                    (workdir / "agent_logs" / "openrouter_error.txt").write_text(
                        str(exc), encoding="utf-8"
                    )
                    steps = 0
        finally:
            gui.stop()
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
    if mode == "openrouter-gui-agent" and not result.success:
        payload["openrouter_log_tail"] = openrouter_log_tail(workdir / "agent_logs")
        error_path = workdir / "agent_logs" / "openrouter_error.txt"
        if error_path.exists():
            payload["openrouter_error"] = error_path.read_text(encoding="utf-8")
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
    if task["id"] == "writer_doc_001":
        create_review_odt(workdir / expected["output_file"])
    else:
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
    _create_starter_document(workdir)


def _create_starter_document(workdir: Path) -> None:
    source = workdir / "starter.txt"
    source.write_text(
        "Q3 Revenue Operations Review\n\nReplace this starter text with the completed review.\n",
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "odt",
                "--outdir",
                str(workdir),
                str(source),
            ],
            check=True,
            text=True,
            capture_output=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        create_odt(workdir / "starter.odt", "Untitled Starter", ["Replace this starter text."])
    finally:
        source.unlink(missing_ok=True)


def _load_known_task_without_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if "writer_doc_001" not in text:
        raise RuntimeError("PyYAML is not installed and fallback only supports task001.yaml")
    return {
        "id": "writer_doc_001",
        "instruction": (
            "Build a polished LibreOffice Writer quarterly business review document "
            "from the provided inputs."
        ),
        "setup": ["starter.odt"],
        "expected": {
            "output_file": "output.odt",
            "title": "Q3 Revenue Operations Review",
            "required_text": [
                "## Executive Summary",
                "Q3 revenue operations closed above plan, with expansion revenue offsetting slower new logo conversion in the enterprise segment.",
                "## KPI Scorecard",
                "Net Revenue Retention",
                "Pipeline Coverage",
                "Forecast Accuracy",
                "Gross Margin",
                "## Regional Performance",
                "North America",
                "EMEA",
                "APAC",
                "## Monthly Revenue And Margin Trend",
                "July",
                "August",
                "September",
                "Revenue",
                "Gross Margin",
                "## Strategic Initiatives",
                "Renewal desk automation",
                "Partner-sourced pipeline",
                "Billing exception cleanup",
                "## Risk Register",
                "Enterprise sales cycle slippage",
                "Data quality backlog",
                "Partner enablement capacity",
                "## Decisions Requested",
                "Approve two incremental data operations contractors for Q4.",
            ],
            "required_tables": [
                "KPI Scorecard",
                "Regional Performance",
                "Strategic Initiatives",
                "Risk Register",
            ],
            "min_tables": 4,
            "required_chart_images": ["Pictures/monthly_revenue_margin_chart.svg"],
            "required_chart_labels": [
                "Monthly Revenue And Margin Trend",
                "July",
                "August",
                "September",
                "Revenue",
                "Gross Margin",
            ],
            "min_chart_images": 1,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument(
        "--mode",
        choices=["shell-baseline", "codex-agent", "openrouter-gui-agent"],
        default="shell-baseline",
    )
    parser.add_argument("--workdir", default="/workspace/run")
    args = parser.parse_args()

    result = run_task(Path(args.task), args.mode, Path(args.workdir))
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
