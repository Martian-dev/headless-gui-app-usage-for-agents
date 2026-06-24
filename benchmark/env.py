from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path


class Environment:
    """Minimal computer-use environment backed by Xvfb, xdotool, and shell."""

    def __init__(self, workspace: Path | str, display: str = ":99") -> None:
        self.workspace = Path(workspace)
        self.display = display
        self._processes: list[subprocess.Popen[str]] = []

    def start_gui(self, document_path: Path | str | None = None) -> None:
        env = self._env()
        self._processes.append(
            subprocess.Popen(
                ["Xvfb", self.display, "-screen", "0", "1920x1080x24"],
                env=env,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        )
        time.sleep(0.5)
        self._processes.append(
            subprocess.Popen(
                ["fluxbox"],
                env=env,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        )
        time.sleep(0.5)

        command = ["libreoffice", "--writer", "--nologo", "--nofirststartwizard", "--norestore"]
        if document_path is not None:
            command.append(str(document_path))
        self._processes.append(
            subprocess.Popen(
                command,
                env=env,
                cwd=self.workspace,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        )
        time.sleep(3)

    def stop(self) -> None:
        for process in reversed(self._processes):
            if process.poll() is None:
                process.terminate()
        for process in reversed(self._processes):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        self._processes.clear()

    def screenshot(self, output_path: Path | str | None = None) -> Path:
        output = Path(output_path) if output_path else self.workspace / "screenshot.png"
        self._run(["scrot", str(output)])
        return output

    def click(self, x: int, y: int, button: int = 1) -> None:
        self._run(["xdotool", "mousemove", str(x), str(y), "click", str(button)])

    def type(self, text: str) -> None:
        self._run(["xdotool", "type", "--delay", "2", text])

    def key(self, key_name: str) -> None:
        self._run(["xdotool", "key", key_name])

    def bash(self, command: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=self.workspace,
            env=self._env(),
            shell=True,
            check=check,
            text=True,
            capture_output=True,
        )

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=self.workspace,
            env=self._env(),
            check=True,
            text=True,
            capture_output=True,
        )

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["DISPLAY"] = self.display
        return env


def shell_quote(value: Path | str) -> str:
    return shlex.quote(str(value))
