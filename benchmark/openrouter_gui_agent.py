from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def run_openrouter_gui_agent(task: dict[str, Any], workdir: Path, logs_dir: Path) -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY in benchmark/.env")

    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "openrouter_gui_agent.jsonl"
    model = os.environ.get("CODEX_MODEL", "google/gemma-4-31b-it:free")
    messages = _initial_messages(task)
    steps = 0

    with log_path.open("w", encoding="utf-8") as log:
        for _ in range(int(os.environ.get("GUI_AGENT_MAX_STEPS", "60"))):
            steps += 1
            response = _chat(api_key, model, messages)
            _log_response(log, response)
            message = response["choices"][0]["message"]
            messages.append(message)

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                break

            for tool_call in tool_calls:
                result = _execute_tool(tool_call, workdir)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": tool_call["function"]["name"],
                        "content": result["text"],
                    }
                )
                if result.get("image_b64"):
                    messages.append(
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Current LibreOffice Writer screenshot."},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{result['image_b64']}"
                                    },
                                },
                            ],
                        }
                    )
    return steps


def openrouter_log_tail(logs_dir: Path, lines: int = 80) -> list[str]:
    log_path = logs_dir / "openrouter_gui_agent.jsonl"
    if not log_path.exists():
        return []
    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        content = handle.readlines()
    return [line.rstrip("\n") for line in content[-lines:]]


def _initial_messages(task: dict[str, Any]) -> list[dict[str, Any]]:
    expected = task["expected"]
    required_lines = "\n".join(f"- {line}" for line in expected["required_text"])
    required_tables = "\n".join(f"- {line}" for line in expected.get("required_tables", []))
    required_chart_labels = "\n".join(
        f"- {line}" for line in expected.get("required_chart_labels", [])
    )
    prompt = f"""You are controlling LibreOffice Writer in a Docker virtual display.

You must complete the task using only physical GUI actions: screenshot, click,
type_text, key, and wait. You do not have shell access. Do not ask for shell,
Python, file helpers, direct ODT writing, or command-line conversion.

Task:
{task["instruction"]}

Input document:
/workspace/run/starter.odt

Required saved artifact:
/workspace/run/{expected["output_file"]}

Required title:
{expected["title"]}

Required document text:
{required_lines}

Required table names:
{required_tables}

Required chart labels:
{required_chart_labels}

Start by calling screenshot. Then operate LibreOffice Writer visually. Save the
document as output.odt in /workspace/run before you finish.
"""
    return [{"role": "user", "content": prompt}]


def _chat(api_key: str, model: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "tools": _tools(),
        "tool_choice": "auto",
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://local.gym-anything-writer",
            "X-Title": "Gym Anything Writer GUI Benchmark",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {body}") from exc


def _execute_tool(tool_call: dict[str, Any], workdir: Path) -> dict[str, str]:
    name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"].get("arguments") or "{}")
    env = os.environ.copy()
    env["DISPLAY"] = os.environ.get("DISPLAY", ":99")

    if name == "screenshot":
        output_path = workdir / "screenshot.png"
        subprocess.run(["scrot", str(output_path)], env=env, check=True, capture_output=True)
        image_b64 = base64.b64encode(output_path.read_bytes()).decode("ascii")
        return {"text": "Screenshot captured.", "image_b64": image_b64}
    if name == "click":
        subprocess.run(
            [
                "xdotool",
                "mousemove",
                str(int(arguments["x"])),
                str(int(arguments["y"])),
                "click",
                str(int(arguments.get("button", 1))),
            ],
            env=env,
            check=True,
            capture_output=True,
        )
        return {"text": f"Clicked {arguments['x']},{arguments['y']}."}
    if name == "type_text":
        subprocess.run(
            ["xdotool", "type", "--delay", "1", str(arguments["text"])],
            env=env,
            check=True,
            capture_output=True,
        )
        return {"text": "Typed text into the active GUI control."}
    if name == "key":
        subprocess.run(
            ["xdotool", "key", str(arguments["key_name"])],
            env=env,
            check=True,
            capture_output=True,
        )
        return {"text": f"Pressed {arguments['key_name']}."}
    if name == "wait":
        seconds = max(0, min(10, float(arguments.get("seconds", 1))))
        time.sleep(seconds)
        return {"text": f"Waited {seconds} seconds."}
    raise RuntimeError(f"Unsupported tool call: {name}")


def _tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "screenshot",
                "description": "Capture the current LibreOffice Writer screen.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "click",
                "description": "Click a coordinate on the virtual display.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "button": {"type": "integer", "default": 1},
                    },
                    "required": ["x", "y"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "type_text",
                "description": "Type text into the active GUI control.",
                "parameters": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "key",
                "description": "Press a keyboard key or shortcut, such as ctrl+s or Return.",
                "parameters": {
                    "type": "object",
                    "properties": {"key_name": {"type": "string"}},
                    "required": ["key_name"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "wait",
                "description": "Wait for the GUI to settle.",
                "parameters": {
                    "type": "object",
                    "properties": {"seconds": {"type": "number", "minimum": 0, "maximum": 10}},
                    "additionalProperties": False,
                },
            },
        },
    ]


def _log_response(log: Any, response: dict[str, Any]) -> None:
    slim = {
        "id": response.get("id"),
        "model": response.get("model"),
        "choices": response.get("choices"),
        "usage": response.get("usage"),
    }
    log.write(json.dumps(slim) + "\n")
    log.flush()
