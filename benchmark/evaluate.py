from __future__ import annotations

import argparse
import json
from pathlib import Path

from runner import run_task


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default=str(Path(__file__).parent / "tasks" / "task001.yaml"))
    parser.add_argument("--mode", choices=["shell-baseline", "codex-agent"], default="shell-baseline")
    parser.add_argument("--workdir", default=str(Path(__file__).parent / "runs" / "task001"))
    args = parser.parse_args()

    result = run_task(Path(args.task), args.mode, Path(args.workdir))
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
