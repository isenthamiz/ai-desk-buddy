# AI Desk Buddy

AI Desk Buddy is a physical AI desk companion with ESP32 firmware and a
Python/FastAPI backend. Milestone 5 targets the available `esp32dev` board; an
ESP32-S3 remains a possible later hardware target.

## Status
Milestone 4 is complete. Milestone 5 physical-device integration is in progress.

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
- Current device: PlatformIO `esp32dev`
- Possible later device: ESP32-S3
- Firmware: C++ / PlatformIO / Arduino framework initially
- Device communication: WebSocket

## Start here
For Codex and contributors:
1. Read `AGENTS.md`.
2. Read `docs/architecture.md`.
3. Review `docs/features.md`.
4. Check `docs/implemented-features.md` for what already exists.
5. Follow `docs/protocol.md`.
6. Implement only the current work in `docs/milestones.md`.
7. Record important architectural changes in `docs/decisions.md`.

## Current milestone
**Milestone 5 — First Real ESP32**

The backend and simulator communicate over WebSocket. Text entered in the simulator
goes through an OpenAI-backed conversation service with deterministic timer and
reminder tools. One-shot reminders are stored in SQLite, survive backend restarts,
and are delivered when an offline device reconnects. The `esp32dev` firmware now
connects over the same WebSocket protocol and provides an SSD1306 face plus
physical timer controls. An optional Open-Meteo integration gives concise current,
today, and tomorrow weather reports for a configured fixed location. An optional
Todoist integration can create, list, and complete tasks using a personal API token.

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

Reminder data defaults to `server/data/buddy.db`. Set `BUDDY_DATABASE_PATH` to use
a different SQLite file. Reminder due times are stored in UTC.

To enable weather reports, configure all four location values in `server/.env`:

```dotenv
BUDDY_WEATHER_LOCATION_NAME=Dublin
BUDDY_WEATHER_LATITUDE=53.3498
BUDDY_WEATHER_LONGITUDE=-6.2603
BUDDY_WEATHER_TIMEZONE=Europe/Dublin
```

Ask Buddy for the weather now, today, or tomorrow. Forecasts come from Open-Meteo,
are cached for ten minutes, and use the existing display and speech messages.
Open-Meteo attribution and usage terms apply.

To enable Todoist task tools, copy your personal token from Todoist Settings →
Integrations → Developer and add it to `server/.env`:

```dotenv
TODOIST_API_TOKEN=your-personal-api-token
```

Restart the backend, then ask Buddy to add a Todoist task, list today's, overdue,
or upcoming tasks, or complete a task it has just created or listed. The token is
secret and must never be committed. AI Desk Buddy is not created by, affiliated
with, or supported by Todoist.

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

## Build and run the physical device

The initial physical target is the available PlatformIO `esp32dev` board using
the Arduino framework. Install PlatformIO Core or use the PlatformIO IDE
extension, then create the local firmware configuration:

```bash
cp firmware/include/config.example.h firmware/include/config.h
```

Edit `firmware/include/config.h` with the Wi-Fi credentials and the backend
computer's LAN IP address. Do not use `127.0.0.1`; from the ESP32 that address
means the ESP32 itself. The local file is ignored by Git and must never be
committed.

Start the backend so it is reachable on the LAN:

```bash
cd server
uv run uvicorn aideskbuddy.main:app --host 0.0.0.0 --port 8000
```

If a different port is used, set the same value in `config.h`. Build, upload,
and monitor the firmware from the repository root:

```bash
pio run --project-dir firmware
pio run --project-dir firmware --target upload
pio device monitor --project-dir firmware
```

The current wiring is:

| Part | Connection |
| --- | --- |
| SSD1306 SDA | GPIO 21 |
| SSD1306 SCL | GPIO 22 |
| SSD1306 I2C address | `0x3C` |
| Increase button | GPIO 25 to GND |
| Decrease button | GPIO 26 to GND |
| Select button | GPIO 32 to GND |
| Cancel button | GPIO 27 to GND |

The buttons use the ESP32's internal pull-ups. On a successful connection, the
serial monitor reports Wi-Fi and WebSocket connection followed by the initial
`IDLE` state. Increase/decrease selects a timer duration, Select starts it, and
Cancel cancels an active timer.

For an end-to-end check:

1. Confirm the serial monitor reports `WebSocket connected` and `Received state: IDLE`.
2. Select and start a short timer using the physical buttons.
3. Confirm the display enters the timer state and counts down.
4. Cancel one timer and confirm the display returns to idle.
5. Let another timer expire and confirm the alert renders.
