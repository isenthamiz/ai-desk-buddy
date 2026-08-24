# AI Desk Buddy

AI Desk Buddy is a physical AI desk companion built around an ESP32-S3 and a Python/FastAPI backend.

## Status
Milestone 3 implemented.

## Planned repository structure

```text
ai-desk-buddy/
├── AGENTS.md
├── README.md
├── docs/
├── server/
├── firmware/
└── simulator/
```

## Technology
- Backend: Python 3.13+, FastAPI, Pydantic, Uvicorn
- Dependency management: `uv`
- Testing: `pytest`
- Device: ESP32-S3
- Firmware: C++ / PlatformIO / Arduino framework initially
- Device communication: WebSocket

## Start here
For Codex and contributors:
1. Read `AGENTS.md`.
2. Read `docs/architecture.md`.
3. Review `docs/features.md`.
4. Follow `docs/protocol.md`.
5. Implement only the current work in `docs/milestones.md`.
6. Record important architectural changes in `docs/decisions.md`.

## Current milestone
**Milestone 3 — Buddy Has Tools**

The backend and simulator communicate over WebSocket. Text entered in the simulator
goes through an OpenAI-backed conversation service with in-memory context. Buddy can
use deterministic tools to set or cancel one in-memory timer per connected device;
the backend owns timer expiry and the simulator renders its countdown and alert.

## Initial backend shape

```text
server/
├── pyproject.toml
└── src/
    └── aideskbuddy/
        └── main.py
```

Additional packages should be introduced as the current milestone needs them rather than creating a large empty architecture up front.

## Local development

Python 3.13 or newer and [`uv`](https://docs.astral.sh/uv/) are required.

Install the backend and development dependencies:

```bash
cd server
uv sync
```

Run the server from the `server/` directory:

```bash
cp .env.example .env
# Edit .env and replace the placeholder API key.
uv run uvicorn aideskbuddy.main:app --reload
```

The server loads `server/.env` automatically. It is ignored by Git; never commit
or share it. The default model is `gpt-5.6-luna`; override `OPENAI_MODEL` in the
same file if desired. The server can start without a key for health checks, but
conversational requests return a graceful configuration error response until the
key is set.

The health endpoint is available at `http://127.0.0.1:8000/health`.

Run the tests from the `server/` directory:

```bash
uv run pytest
```

The `simulator/` directory contains the visual device simulator and local
developer controls.

## Run the connected device simulator

Start the backend in one terminal:

```bash
cd server
.venv/bin/uvicorn aideskbuddy.main:app --reload
```

Start the visual device simulator in another terminal:

```bash
cd simulator
.venv/bin/buddy-simulator
```

The simulator connects to `ws://127.0.0.1:8000/ws/device`, identifies itself as
`simulator-001`, and displays a green `CONNECTED` indicator. Use `F` for an
action-button event, `P` for presence, and `T` for temporary text input.
Ask Buddy to set or cancel a timer through the `T` text input.
