# Minimal Gym-Anything-Style Writer Benchmark

This directory contains a small end-to-end benchmark inspired by the Gym-Anything
architecture:

```text
Task
  -> Environment
  -> Codex agent
  -> Actions
  -> Application state / output artifact
  -> Verifier
  -> Score
```

The first target application is LibreOffice Writer. The task asks Codex to build
a quarterly business review document with multiple sections, tables, and an
embedded chart, then save it as `output.odt`.

The key design choice is deterministic verification. The benchmark does not
judge screenshots. It opens the produced ODT file, extracts text from the
document XML, and checks exact expected content.

## What This Uses

The Docker image installs:

- Ubuntu 24.04
- LibreOffice Writer
- Xvfb
- fluxbox
- x11vnc
- xdotool
- scrot
- Python
- Codex CLI `0.139.0`

The main pieces are:

- `LibreOffice Writer`: the application under test.
- `Xvfb`: a virtual display server so GUI apps can run in Docker.
- `fluxbox`: a lightweight window manager for the virtual desktop.
- `xdotool`: mouse, keyboard, and typing automation.
- `scrot`: screenshot capture from the virtual display.
- `codex exec`: the real Codex agent runner.
- `verifier.py`: deterministic artifact verification for the ODT output.

## Layout

```text
benchmark/
├── Dockerfile
├── README.md
├── codex_agent.py
├── env.py
├── evaluate.py
├── gui_smoke.py
├── odt_utils.py
├── runner.py
├── task_files/
│   └── README.md
├── tasks/
│   └── task001.yaml
├── tests/
│   └── test_verifier.py
└── verifier.py
```

## Current Task

The active task is `writer_doc_001` in `tasks/task001.yaml`.

Codex starts with:

```text
/workspace/run/starter.odt
```

It must produce:

```text
/workspace/run/output.odt
```

The expected document title is:

```text
Q3 Revenue Operations Review
```

The verifier also checks required sections, four named tables, an embedded SVG
chart image, and chart labels such as July, August, September, Revenue, and
Gross Margin.

## How The Codex Run Works

The default Docker command runs `runner.py` in `openrouter-gui-agent` mode.

The flow is:

1. Load `tasks/task001.yaml`.
2. Reset `/workspace/run`.
3. Create a fresh `starter.odt`.
4. Start the virtual GUI and open `starter.odt` in LibreOffice Writer.
5. Send screenshots to the OpenRouter model and expose only physical GUI actions.
6. The agent clicks, types, presses keys, waits, and screenshots inside the container.
7. The runner verifies `/workspace/run/output.odt`.
8. The runner prints a JSON result.

A successful result looks like:

```json
{
  "task": "writer_doc_001",
  "success": true,
  "score": 1,
  "steps": 12,
  "missing": [],
  "output_file": "/workspace/run/output.odt"
}
```

If Codex fails, the JSON includes the tail of the Codex log and the files left in
the work directory.

## How The Agent Interacts With Writer

The live default path is `openrouter-gui-agent`, a direct OpenRouter tool loop
using `google/gemma-4-31b-it:free`.

Before Codex starts, `runner.py` launches:

```text
Xvfb -> fluxbox -> LibreOffice Writer
```

The model receives screenshots and can call only low-level computer-use tools:

```python
screenshot()
click(x, y)
type_text(text)
key(key_name)
wait(seconds)
```

No document creation helper is exposed. The agent has to observe Writer and take
physical actions. Shell commands are not part of this loop.

The experimental `codex-agent` mode also disables the Codex shell tool with:

```toml
[features]
shell_tool = false
```

In testing, Codex CLI `0.139.0` with the current OpenRouter custom-provider
configuration accepted the MCP server config but did not surface the MCP tools
into `codex exec`; the model attempted `screenshot` and Codex rejected it as an
unsupported call. For true physical-action testing with OpenRouter, use the
default `openrouter-gui-agent` mode.

The deterministic verifier still evaluates the final artifact,
`/workspace/run/output.odt`, after the agent finishes.

## Auth And Provider Setup

Live Codex runs need a model provider and credentials. The default setup in this
scaffold uses OpenRouter with:

```text
google/gemma-4-31b-it:free
```

Edit:

```text
benchmark/.env
```

Set:

```text
OPENROUTER_API_KEY=...
CODEX_MODEL_PROVIDER=openrouter
CODEX_MODEL=google/gemma-4-31b-it:free
```

The default `openrouter-gui-agent` mode calls OpenRouter directly with
`OPENROUTER_API_KEY`. The experimental `codex-agent` mode writes this Codex user
config inside the container at `/tmp/codex-home/config.toml`:

```toml
model = "google/gemma-4-31b-it:free"
model_provider = "openrouter"

[model_providers.openrouter]
name = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
```

That tells Codex CLI to call OpenRouter's OpenAI-compatible API instead of the
built-in OpenAI provider. The OpenRouter key stays in the environment; it is not
written into the config file.

Alternative OpenAI/Codex auth modes are still available:

```text
CODEX_AUTH_B64=...
OPENAI_API_KEY=...
```

`CODEX_AUTH_B64` must be a real Codex `auth.json` encoded as one line of base64.

Optional private CA support remains available:

```text
CODEX_CA_B64=...
```

`CODEX_CA_B64` is only needed if the proxy presents a certificate signed by a
private/internal CA. A missing CA commonly shows up as:

```text
invalid peer certificate: UnknownIssuer
```

## Build And Run

Build the Docker image:

```bash
docker build -t gym-anything-writer ./benchmark
```

Run the live physical GUI benchmark:

```bash
docker run --rm --env-file benchmark/.env gym-anything-writer
```

The default image command currently runs `openrouter-gui-agent`.

To explicitly run the Codex CLI MCP experiment:

```bash
docker run --rm --env-file benchmark/.env gym-anything-writer \
  python3 /workspace/benchmark/runner.py \
  --task /workspace/benchmark/tasks/task001.yaml \
  --mode codex-agent
```

Run the deterministic non-agent baseline:

```bash
docker run --rm gym-anything-writer \
  python3 /workspace/benchmark/runner.py \
  --task /workspace/benchmark/tasks/task001.yaml \
  --mode shell-baseline
```

Run the local baseline without Docker:

```bash
python3 benchmark/evaluate.py --mode shell-baseline
```

Run verifier tests:

```bash
python3 -m unittest discover -s benchmark/tests
```

## GUI Smoke Test

The GUI environment is provided by `env.py`.

It exposes:

```python
env.screenshot()
env.click(500, 300)
env.type("Hello")
env.key("ctrl+s")
```

`start_gui()` launches:

```text
Xvfb -> fluxbox -> LibreOffice Writer
```

`gui_smoke.py` can be used to verify that the virtual display and Writer launch
correctly inside the container.

## NOTE

The deterministic `shell-baseline` mode still exists as a verifier sanity check.
It is not the agent benchmark. The live `openrouter-gui-agent` mode is the
physical GUI test.
