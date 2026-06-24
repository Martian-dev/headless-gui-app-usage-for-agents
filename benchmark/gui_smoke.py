from __future__ import annotations

import json
from pathlib import Path

from env import Environment
from odt_utils import create_odt


def main() -> int:
    workdir = Path("/workspace/gui-smoke")
    workdir.mkdir(parents=True, exist_ok=True)
    starter = workdir / "starter.odt"
    create_odt(starter, "GUI Smoke Test", ["LibreOffice should open this document."])

    env = Environment(workdir)
    try:
        env.start_gui(starter)
        screenshot = env.screenshot(workdir / "screenshot.png")
    finally:
        env.stop()

    result = {
        "success": screenshot.exists() and screenshot.stat().st_size > 0,
        "screenshot": str(screenshot),
        "bytes": screenshot.stat().st_size if screenshot.exists() else 0,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
