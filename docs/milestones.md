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

## Milestone 5 — First Real ESP32

### Goal
Replace the simulator with a physical ESP32-S3 for basic connectivity and controls.

Planned work:
- PlatformIO firmware project
- Wi-Fi
- WebSocket connection
- protocol parsing
- display abstraction
- physical input abstraction
- basic state rendering

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
