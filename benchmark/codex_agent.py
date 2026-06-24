from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


REMOTE_CODEX_HOME = Path("/tmp/codex-home")
REMOTE_CODEX_SECRETS_DIR = Path("/tmp/codex-secrets")


def run_codex_agent(task: dict[str, Any], workdir: Path, logs_dir: Path) -> int:
    logs_dir.mkdir(parents=True, exist_ok=True)
    _setup_codex_auth()

    prompt = _build_prompt(task)
    model = os.environ.get("CODEX_MODEL", "gpt-5")
    model_provider = os.environ.get("CODEX_MODEL_PROVIDER")
    reasoning_effort = os.environ.get("CODEX_REASONING_EFFORT")
    output_path = logs_dir / "codex.jsonl"

    command = [
        "codex",
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "--model",
        model,
        "--json",
    ]
    if model_provider:
        command.extend(["-c", f'model_provider="{model_provider}"'])
    if reasoning_effort:
        command.extend(["-c", f"model_reasoning_effort={reasoning_effort}"])
    command.extend(["--", prompt])

    env = _codex_env()
    with output_path.open("w", encoding="utf-8") as output:
        process = subprocess.run(
            command,
            cwd=workdir,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )

    _copy_sessions(logs_dir)
    return _count_codex_events(output_path) or (1 if process.returncode == 0 else 0)


def _build_prompt(task: dict[str, Any]) -> str:
    expected = task["expected"]
    required_lines = "\n".join(f"- {line}" for line in expected["required_text"])
    required_tables = "\n".join(f"- {line}" for line in expected.get("required_tables", []))
    required_chart_labels = "\n".join(
        f"- {line}" for line in expected.get("required_chart_labels", [])
    )
    return f"""You are inside a Dockerized LibreOffice Writer benchmark environment.

Task:
{task["instruction"]}

Current directory:
/workspace/run

Input file:
/workspace/run/starter.odt

Required final artifact:
/workspace/run/{expected["output_file"]}

Shell access is disabled for this benchmark. You must operate LibreOffice Writer
through the GUI only.

Use only the available computer-use tools:
- screenshot: observe the current LibreOffice Writer window.
- click: click a screen coordinate.
- type_text: type text into the active GUI control.
- key: press keyboard shortcuts such as ctrl+a, ctrl+s, alt+f, or Return.
- wait: wait for the GUI to settle.

Do not call or request bash, Python, direct ODT writing, file helpers,
LibreOffice command-line conversion, or any non-GUI file operation.

Create or edit the document so the verifier can extract the following exact content from the ODT:

Title:
{expected["title"]}

Required document text:
{required_lines}

Required table names:
{required_tables}

Required chart labels:
{required_chart_labels}

Important constraints:
- Work only in the current directory.
- Save the finished artifact exactly as /workspace/run/{expected["output_file"]}.
- Do not modify the benchmark source files under /workspace/benchmark.
- When done, briefly report what file you produced.
"""


def _setup_codex_auth() -> None:
    REMOTE_CODEX_HOME.mkdir(parents=True, exist_ok=True)
    REMOTE_CODEX_SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    auth_path = REMOTE_CODEX_SECRETS_DIR / "auth.json"

    codex_auth_b64 = os.environ.get("CODEX_AUTH_B64")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")

    _setup_ca_bundle()

    if openrouter_api_key:
        _write_openrouter_config()
        _remove_codex_auth_link()
        return

    if codex_auth_b64:
        decoded = subprocess.run(
            ["base64", "-d"],
            input=codex_auth_b64,
            text=True,
            capture_output=True,
            check=True,
        )
        auth_path.write_text(decoded.stdout, encoding="utf-8")
    elif openai_api_key:
        auth_path.write_text(json.dumps({"OPENAI_API_KEY": openai_api_key}, indent=2), encoding="utf-8")
    else:
        raise RuntimeError(
            "Missing Codex auth. Set OPENROUTER_API_KEY, CODEX_AUTH_B64, or OPENAI_API_KEY "
            "in benchmark/.env."
        )

    auth_path.chmod(0o600)
    codex_auth_path = REMOTE_CODEX_HOME / "auth.json"
    _remove_codex_auth_link()
    codex_auth_path.symlink_to(auth_path)


def _write_openrouter_config() -> None:
    model = os.environ.get("CODEX_MODEL", "google/gemma-4-31b-it:free")
    os.environ["CODEX_MODEL_PROVIDER"] = os.environ.get("CODEX_MODEL_PROVIDER", "openrouter")
    config_path = REMOTE_CODEX_HOME / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                f'model = "{model}"',
                'model_provider = "openrouter"',
                "",
                "[model_providers.openrouter]",
                'name = "OpenRouter"',
                'base_url = "https://openrouter.ai/api/v1"',
                'env_key = "OPENROUTER_API_KEY"',
                "",
                "[features]",
                "shell_tool = false",
                "",
                "[mcp_servers.writer_environment]",
                'command = "node"',
                'args = ["/workspace/benchmark/mcp_gui_server.mjs"]',
                'env = { WRITER_WORKDIR = "/workspace/run", DISPLAY = ":99" }',
                'enabled_tools = ["screenshot", "click", "type_text", "key", "wait"]',
                'default_tools_approval_mode = "approve"',
                "required = true",
                "startup_timeout_sec = 20",
                "tool_timeout_sec = 60",
                "",
            ]
        ),
        encoding="utf-8",
    )
    config_path.chmod(0o600)


def _remove_codex_auth_link() -> None:
    codex_auth_path = REMOTE_CODEX_HOME / "auth.json"
    if codex_auth_path.exists() or codex_auth_path.is_symlink():
        codex_auth_path.unlink()


def _setup_ca_bundle() -> None:
    codex_ca_b64 = os.environ.get("CODEX_CA_B64")
    if not codex_ca_b64:
        return

    parsewave_only = Path("/tmp/parsewave-ca.pem.parsewave-only")
    ca_path = Path("/tmp/parsewave-ca.pem")
    decoded = subprocess.run(
        ["base64", "-d"],
        input=codex_ca_b64,
        text=True,
        capture_output=True,
        check=True,
    )
    parsewave_only.write_text(decoded.stdout, encoding="utf-8")

    system_candidates = [
        Path("/etc/ssl/certs/ca-certificates.crt"),
        Path("/etc/pki/tls/certs/ca-bundle.crt"),
    ]
    system_bundle = next((path for path in system_candidates if path.exists()), None)
    if system_bundle:
        ca_path.write_bytes(system_bundle.read_bytes() + parsewave_only.read_bytes())
    else:
        ca_path.write_bytes(parsewave_only.read_bytes())

    parsewave_only.unlink(missing_ok=True)
    ca_path.chmod(0o644)
    os.environ["SSL_CERT_FILE"] = str(ca_path)


def _codex_env() -> dict[str, str]:
    env = os.environ.copy()
    env["CODEX_HOME"] = str(REMOTE_CODEX_HOME)
    benchmark_path = "/workspace/benchmark"
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{benchmark_path}:{existing_pythonpath}" if existing_pythonpath else benchmark_path
    )
    return env


def codex_log_tail(logs_dir: Path, lines: int = 80) -> list[str]:
    log_path = logs_dir / "codex.jsonl"
    if not log_path.exists():
        return []
    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        content = handle.readlines()
    return [line.rstrip("\n") for line in content[-lines:]]


def _copy_sessions(logs_dir: Path) -> None:
    sessions = REMOTE_CODEX_HOME / "sessions"
    if not sessions.exists():
        return
    subprocess.run(["cp", "-R", str(sessions), str(logs_dir / "sessions")], check=False)


def _count_codex_events(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            count += 1
    return count
