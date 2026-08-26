# AI Desk Buddy Milestones

The project should be built vertically and incrementally. Do not implement later milestones prematurely.

## Milestone 1 — Buddy Is Alive

### Goal
Prove the basic architecture without physical hardware.

At completion:
- FastAPI server starts locally.
- A simulator connects through WebSocket.
- Server recognizes the simulator/device.
- Simulator can send simple events/text.
- Server can send state/display/speak messages.
- Tests cover the protocol boundary and core behavior.

### Tasks
1. Create repository/module skeleton.
2. Create Python backend using Python 3.13+, FastAPI, Pydantic, Uvicorn, `uv`, and `pytest`.
3. Define minimal protocol models from `protocol.md`.
4. Define initial `BuddyState`.
5. Implement WebSocket device endpoint.
6. Track a connected simulator/device session in memory.
7. Create a simple Python CLI simulator.
8. Connect simulator ↔ backend.
9. Support `USER_TEXT` with an echo/static response first.
10. Add tests.
11. Add local run instructions to README.

### Non-goals
- OpenAI integration
- microphone/audio streaming
- timers/reminders
- persistence
- real ESP32
- wake word
- calendar
- UI/config portal

## Milestone 2 — Buddy Can Think

### Goal
Add text-based AI conversation while keeping hardware out of the loop.

Planned work:
- AI provider abstraction
- OpenAI Python SDK integration
- concise Buddy system instructions
- conversation context
- `THINKING` → `SPEAKING` → `IDLE` flow
- graceful provider errors
- tests with mocked AI provider

## Milestone 3 — Buddy Has Tools

### Goal
Introduce deterministic actions, beginning with timers.

Planned work:
- tool abstraction
- set/cancel timer
- timer lifecycle
- device countdown/status messages as needed
- completion alert
- focus-mode foundations

Initial scope decisions:
- one active, in-memory timer per connected device
- backend-authoritative expiry with device-side countdown rendering
- AI function calls execute deterministic timer tools
- no pause/resume, named timers, persistence, or full Pomodoro workflow yet

## Milestone 4 — Reminders & Durable State

### Goal
Add reminders and persistence.

Planned work:
- reminder model/service
- durable storage
- restore relevant state after restart
- reminder notifications
- define persistence choice based on actual requirements

### Implemented scope
- one-shot reminders created/cancelled through deterministic AI tools
- SQLite persistence with UTC due times
- pending reminder restoration after backend restart
- offline-device deferral and delivery on reconnect
- alert/display/speak notification flow in the simulator

Recurring reminders, snoozing, reminder-management UI, and calendar integration are
deferred.

## Milestone 5 — First Real ESP32

### Goal
Replace the simulator with the available physical `esp32dev` board for basic
connectivity and controls.

Planned work:
- PlatformIO firmware project
- Wi-Fi
- WebSocket connection
- protocol parsing
- display abstraction
- physical input abstraction
- basic state rendering

### Implemented scope

- PlatformIO/Arduino firmware targeting the available `esp32dev` board
- Wi-Fi and reconnecting WebSocket client
- `ESP32` device registration using the same public protocol as the simulator
- SSD1306 display abstraction with state, timer, and alert rendering
- debounced active-low button abstraction
- physical timer selection, start, cancel, and alert acknowledgement controls
- backend protocol support and integration tests for hardware timer controls

Milestone 5 remains in progress until the documented firmware can be freshly
built, flashed, and verified end-to-end on the physical board. Rendering of
general `DISPLAY_TEXT`, `SPEAK`, and reminder content is also still pending.

### Incremental feature — Weather report

- backend-only `get_weather` AI tool for `now`, `today`, and `tomorrow`
- one fixed location configured through environment variables
- provider-neutral service with an Open-Meteo adapter
- ten-minute in-memory cache and graceful provider failures
- existing `DISPLAY_TEXT` and `SPEAK` output; no new device protocol messages

Free-form place lookup, automatic location detection, severe-weather alerts,
scheduled reports, and persistent weather data are deferred.

### Incremental feature — Todoist tasks

- optional single-user authentication through a personal API token
- provider-neutral service with a Todoist API v1 adapter
- deterministic tools to create Inbox tasks, list up to five tasks for today,
  overdue, or the upcoming seven days, and complete a task by exact ID
- existing conversational display and speech output; no new device messages
- Todoist tasks remain separate from Buddy's durable reminders

OAuth, projects, sections, labels, assignments, editing, deletion, background
synchronization, and Todoist-driven Buddy alerts are deferred.

## Milestone 6 — Voice

### Goal
Support push-to-talk voice conversations.

Planned work:
- microphone capture
- audio transfer strategy
- speech-to-text
- AI request
- text-to-speech
- speaker playback
- listening/thinking/speaking animations

Wake word is explicitly deferred.

## Milestone 7 — Presence & Touch

### Goal
Make the physical buddy react naturally to desk presence and touch.

Planned work:
- presence sensor integration
- wake/sleep behavior
- touch events
- inactivity policy
- display/power behavior

## Later milestones
Prioritize based on usefulness after the core experience works:
- calendar & meetings
- computer notifications
- developer mode
- quick notes
- desk dashboard
- morning briefing
- end-of-day mode
- fun/easter eggs
- device configuration UI
- OTA/device management
- wake word
