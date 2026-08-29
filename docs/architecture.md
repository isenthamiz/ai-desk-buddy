# AI Desk Buddy Architecture

## Goal
Build a small physical desk companion that can interact through a display, voice, touch/controls, presence sensing, sounds, timers, reminders, AI tools, and developer-oriented features.

The design intentionally separates the physical device from the higher-level intelligence.

## High-level architecture

```text
┌──────────────────────┐
│      ESP32-S3        │
│                      │
│ Display / animations │
│ Microphone           │
│ Speaker              │
│ Buttons / controls   │
│ Touch                │
│ Presence             │
│ Wi-Fi                │
└──────────┬───────────┘
           │
           │ WebSocket
           ▼
┌──────────────────────┐
│   FastAPI Backend    │
│                      │
│ Device management    │
│ Conversation         │
│ AI orchestration     │
│ Timers               │
│ Reminders            │
│ Tools                │
│ Audio services       │
│ Integrations         │
└──────────┬───────────┘
           │
           ▼
   External services/APIs
```

## Responsibility split

### ESP32-S3
The ESP32 is the physical interface.

It should handle:
- display rendering and animations
- microphone capture
- speaker/audio playback
- physical buttons/controls
- touch input
- presence sensor input
- Wi-Fi connectivity
- local device status
- sending device/user events
- receiving commands/state updates

It should not own general AI orchestration, conversation history, reminders, calendar integrations, or other backend business logic.

### Backend
The backend is the main application brain.

It should handle:
- connected-device sessions
- buddy state/orchestration
- AI conversations
- AI tool execution
- timers and focus sessions
- reminders
- speech processing orchestration
- external integrations
- configuration that is not inherently hardware-local
- persistence when required

## Backend technology
- Python 3.13+
- FastAPI
- Pydantic
- Uvicorn
- `uv`
- `pytest`

Suggested package layout:

```text
server/
├── pyproject.toml
└── src/
    └── aideskbuddy/
        ├── main.py
        ├── ai/
        ├── audio/
        ├── config/
        ├── conversation/
        ├── device/
        ├── protocol/
        ├── reminder/
        ├── timer/
        └── tools/
```

This is guidance, not a requirement to create empty packages before they are needed.

## Communication
WebSocket is the primary device/backend channel because the connection is bidirectional and long-lived.

REST can be added for operations that naturally fit request/response semantics, such as health/configuration endpoints.

The Buddy Control Center is a standalone Expo/React Native application for web,
iPhone, and future Android use. It uses a separate client-facing REST API. App
actions call backend services, and those services send the existing device protocol
messages to the simulator or firmware. The app does not connect to a device or
manufacture device protocol messages directly.

See `protocol.md`.

## Device simulator
Hardware availability must not block backend development.

A simulator should behave like a device client and use the same public protocol as the ESP32. It should be able to:
- connect/disconnect
- send representative device events
- send text input for early AI testing
- print server state/commands
- simulate presence and physical controls

The simulator can be a small Python CLI using the same protocol definitions or JSON schema as the server where practical.

## Buddy state model
Initial conceptual states:

```text
SLEEPING
IDLE
LISTENING
THINKING
SPEAKING
TIMER
ALERT
OFFLINE
ERROR
```

The exact transition model should evolve incrementally. Avoid building a complex state-machine framework until behavior requires it.

Typical conversational flow:

```text
SLEEPING --presence--> IDLE
IDLE --talk/input--> LISTENING
LISTENING --request sent--> THINKING
THINKING --response ready--> SPEAKING
SPEAKING --finished--> IDLE
```

## AI tool architecture
Actions should be explicit tools/services rather than free-form side effects from model text.

Examples:
- set timer
- cancel timer
- create reminder
- get current time
- show a message
- change volume
- future calendar/developer integrations

The AI layer chooses an action; deterministic application code executes it.

Private Obsidian retrieval is a separate path rather than an AI tool. Explicit
`notes:` input bypasses the OpenAI conversation service and its history. The main
backend sends only the question over an authenticated loopback connection to the
separately run note server. That process performs live keyword scanning, obtains
vector candidates from Supabase by opaque chunk ID and reads only selected vault
passages. OpenAI creates embeddings and generates the grounded answer from those
selected passages. Only the final answer and citations cross back into the main
backend.

## Async model
Network-heavy work should use async APIs where possible:
- WebSocket handling
- OpenAI/API requests
- speech services
- external integrations

CPU-heavy work should not block the main event loop. If needed later, isolate it using an executor/process or separate service.

## Persistence
Do not require persistence for the first connectivity milestone.

Durable reminders use a Supabase PostgreSQL table through an async repository.
Without Supabase configuration the development backend uses non-durable in-memory
reminders. Note reconciliation state lives alongside embeddings in Supabase; the
Obsidian vault remains the plaintext source of truth.

## Deployment
During development, the FastAPI backend can run on the developer machine with Uvicorn.

Future deployment could be:
- local desktop/server
- Raspberry Pi or similar local host
- cloud-hosted backend

The ESP32 protocol should not depend on one deployment model.
