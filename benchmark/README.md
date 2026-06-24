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

The first target application is LibreOffice Writer. The task is intentionally
small but more realistic than a "Hello World" title edit: Codex must produce a
short operations handoff document and save it as `output.odt`.

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
Nightly Data Refresh Handoff
```

The verifier also checks for required sections such as purpose, schedule,
validation checklist, and escalation text.

## How The Codex Run Works

The default Docker command runs `runner.py` in `codex-agent` mode.

The flow is:

1. Load `tasks/task001.yaml`.
2. Reset `/workspace/run`.
3. Create a fresh `starter.odt`.
4. Start `codex exec` from `/workspace/run`.
5. Give Codex the task instruction, input path, required output path, and exact
   verifier expectations.
6. Codex acts inside the container.
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

## How Codex Interacts With Writer

This scaffold is a computer-use-plus-shell setup.

Codex has shell access inside Docker, and the environment also contains GUI
automation primitives. That means Codex can currently solve the task in either
of these ways:

- Use LibreOffice Writer through the virtual GUI.
- Use shell tools or Python helpers to create a valid ODT artifact directly.

The prompt currently permits both approaches:

```text
You have shell access and may use LibreOffice headless or direct ODT manipulation.
```

This is intentional for the first milestone. The goal is to prove that the full
benchmark loop works:

```text
Docker packaging -> Codex execution -> artifact creation -> deterministic verification
```

Once that passes consistently, the next stricter milestone is to remove or limit
the direct ODT helper path and require actions through:

```python
screenshot()
click(x, y)
type(text)
key(key_name)
```

That would turn this into a more purely visual computer-use benchmark.

## Auth And Proxy Setup

Live Codex runs require real Codex auth.

Edit:

```text
benchmark/.env
```

Set one auth mode:

```text
CODEX_AUTH_B64=...
```

or:

```text
OPENAI_API_KEY=...
```

`CODEX_AUTH_B64` must be a real Codex `auth.json` encoded as one line of base64.
Proxy variables do not replace auth.

Optional proxy transport settings:

```text
CODEX_HTTPS_PROXY=...
CODEX_HTTP_PROXY=...
CODEX_PARSEWAVE_TOKEN=...
```

Optional private CA support:

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

Run the live Codex-agent benchmark:

```bash
docker run --rm --env-file benchmark/.env gym-anything-writer
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
env.bash("ls -la")
```

`start_gui()` launches:

```text
Xvfb -> fluxbox -> LibreOffice Writer
```

`gui_smoke.py` can be used to verify that the virtual display and Writer launch
correctly inside the container.

## NOTE

This is already a true Codex-agent benchmark when run in `codex-agent` mode, but
it is not yet a pure GUI-only benchmark. Because shell access is enabled, Codex
can bypass the visible Writer UI and create the ODT directly.

That is acceptable for the current stage. It validates the benchmark plumbing
before adding stricter GUI-only constraints.
