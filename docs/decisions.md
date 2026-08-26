# Architecture Decisions

This is a lightweight decision log. Add entries when a decision affects future implementation.

## ADR-001 — Project name
**Decision:** Use `AI Desk Buddy`.

Repository name: `ai-desk-buddy`.

## ADR-002 — Backend language/framework
**Decision:** Python 3.13+ with FastAPI, Pydantic, Uvicorn, `uv`, and `pytest`.

**Reason:** The backend is primarily orchestration around WebSockets, AI APIs, audio/speech services, timers, reminders, and integrations. Python keeps development simple and fast while providing strong libraries for AI/audio experimentation.

## ADR-003 — Device/backend responsibility split
**Decision:** Keep high-level AI and business logic in the backend.

The ESP32-S3 is primarily responsible for physical I/O, connectivity, presentation, and audio capture/playback.

**Reason:** This reduces firmware complexity and makes the backend reusable with the simulator or future device implementations.

## ADR-004 — Primary device transport
**Decision:** Use WebSocket as the primary ESP32/simulator ↔ backend transport.

**Reason:** Device communication is bidirectional and benefits from a long-lived connection.

REST may still be used where request/response semantics make more sense.

## ADR-005 — Develop without hardware first
**Decision:** Build a software device simulator before the hardware arrives.

**Reason:** Backend architecture, protocol, state behavior, AI integration, and tool behavior can be developed and tested independently of hardware.

## ADR-006 — Voice activation
**Decision:** Start with push-to-talk when voice is introduced. Wake-word support is deferred.

**Reason:** Wake-word detection adds complexity and should not block the core voice experience.

## ADR-007 — Persistence
**Decision:** No database is required for Milestone 1.

Choose persistence when durable features such as reminders require it. SQLite is a candidate for a simple local deployment; PostgreSQL can be considered if requirements grow.

## ADR-008 — Feature scope
**Decision:** Desk environmental sensing and smart-home integration are not core project features.

The daily-information concept is framed as a lightweight **Desk Dashboard**, rather than making weather/environment data central.

## ADR-009 — Python dependency management
**Decision:** Use `uv`.

**Reason:** Keep Python environment/dependency management simple and reproducible.

## ADR-010 — Async backend I/O
**Decision:** Prefer async APIs for WebSockets and network integrations.

**Reason:** The backend is expected to maintain long-lived connections and perform network-heavy AI/speech/integration calls.

## ADR-011 — Initial AI conversation integration
**Decision:** Put AI generation behind a provider-neutral async interface and use
OpenAI's Responses API for the first provider. Keep a bounded conversation history
in backend memory for each device connection.

Use `gpt-5.6-luna` as the default text model, configurable through `OPENAI_MODEL`,
and read credentials only from `OPENAI_API_KEY`.

**Reason:** The abstraction keeps conversation orchestration testable and separates
vendor SDK details. Local bounded history is sufficient for Milestone 2 and avoids
premature persistence. The default model fits short, cost- and latency-sensitive
desk-companion conversations while remaining easy to override.

## ADR-012 — Milestone 3 timer scope
**Decision:** Support one backend-owned, in-memory timer per connected device. AI
function calls invoke deterministic `set_timer` and `cancel_timer` tools. The device
renders the countdown from protocol events, while backend expiry is authoritative.

Timer state is intentionally not restored after a disconnect or server restart.
Persistence remains deferred until Milestone 4.

**Reason:** A single timer proves the tool and lifecycle architecture with minimal
state coordination. Multiple/named timers, pausing, and full focus sessions can be
added when product behavior requires them.

## ADR-013 — Milestone 4 durable storage
**Decision:** Use SQLite through Python's standard library for one-shot reminders.
Store timezone-aware due times in UTC, keep pending reminders durable while a device
is offline, and mark them delivered only after their notification is sent.

**Reason:** A single local backend does not require an ORM, database server, or
message broker. A repository boundary keeps future storage changes possible.

## ADR-014 — Initial physical development board

**Decision:** Target the available PlatformIO `esp32dev` board for Milestone 5,
while keeping hardware interaction behind display, input, and network boundaries.
The protocol continues to identify physical firmware with device type `ESP32`.

**Reason:** The available hardware is a standard ESP32 development board rather
than an ESP32-S3. It is sufficient to prove physical connectivity, controls, and
display rendering. Hardware abstractions limit the work needed to move to an
ESP32-S3 later when voice or other hardware requirements demand it.

## ADR-015 — Initial weather reporting

**Decision:** Add weather as a backend AI tool for one fixed, explicitly configured
location. Use a provider-neutral async boundary with Open-Meteo as the initial
adapter, cache each report period in memory for ten minutes, and reuse the existing
conversation display/speech messages.

The initial periods are `now`, `today`, and `tomorrow`. Automatic location
detection, free-form geocoding, scheduled reports, alerts, and weather persistence
are deferred.

**Reason:** A desk device normally stays in one place. Explicit coordinates are
predictable and privacy-preserving, while a provider boundary avoids coupling the
Buddy's business logic to Open-Meteo. Existing protocol messages already express
the required user experience.

## ADR-016 — Initial Todoist integration

**Decision:** Integrate Todoist through a provider-neutral async service and the
current Todoist API v1. The single-user development deployment reads a personal API
token from `TODOIST_API_TOKEN`; OAuth is deferred until multi-user configuration is
required.

Expose deterministic tools to create Inbox tasks, list at most five active tasks for
`today`, `overdue`, or `upcoming`, and complete a task using its exact Todoist ID.
Todoist tasks and Buddy reminders remain separate. Reuse the existing conversation
device messages.

**Reason:** These operations cover useful hands-free task capture and review without
requiring synchronization, conflict resolution, new device protocol messages, or a
configuration UI. Exact-ID completion prevents ambiguous task names from causing an
unintended mutation.
