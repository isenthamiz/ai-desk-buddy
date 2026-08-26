# AI Desk Buddy — Codex Instructions

## Project
AI Desk Buddy is a physical AI companion built around an ESP32-S3 and a Python/FastAPI backend.

The repository is the source of truth. Read the relevant files in `docs/` before making architectural or protocol changes.

## Repository layout
- `server/` — Python + FastAPI backend
- `firmware/` — ESP32-S3 firmware using C++ / PlatformIO / Arduino framework initially
- `simulator/` — software device simulator used before and alongside hardware
- `apps/buddy-control/` — Expo/React Native control app for web and mobile
- `docs/` — architecture, features, protocol, milestones, and decisions

## Backend conventions
- Python 3.13+
- FastAPI
- Pydantic
- Uvicorn
- `uv` for dependency/environment management
- `pytest` for tests
- Prefer package-by-feature.
- Keep API/WebSocket handlers thin.
- Put business logic in services/domain modules.
- Use Pydantic models for protocol/API validation.
- Keep external services such as OpenAI behind small interfaces/adapters.
- Prefer async I/O for WebSockets, HTTP APIs, and other network operations.
- Avoid unnecessary global mutable state.
- Add type hints to public functions and important internal boundaries.
- Unit-test business logic.
- Integration-test API/WebSocket boundaries.
- Do not introduce a database, message broker, or other infrastructure until a milestone requires it.

## Firmware conventions
- ESP32-S3
- C++
- PlatformIO
- Arduino framework initially
- Firmware owns hardware interaction and presentation, not AI/business logic.

## Communication
The device and backend primarily communicate over WebSocket.
Protocol messages are documented in `docs/protocol.md`.

Do not silently invent or change protocol messages. Update `docs/protocol.md` whenever the protocol changes.

## Engineering principles
- Implement incrementally by milestone.
- Prefer the simplest implementation that satisfies the current milestone.
- Avoid premature abstractions.
- Do not implement future milestone features unless needed by the current task.
- Update `docs/implemented-features.md` in the same change whenever a feature is
  added, materially changed, or removed. Record only behavior that is actually
  implemented, including important limitations; keep planned work in
  `docs/features.md` or `docs/milestones.md`.
- Keep hardware-specific code behind abstractions where practical so the simulator can exercise the same concepts.
- Run relevant tests before completing a task.
- If requirements are ambiguous or conflict with the docs, call out the ambiguity rather than guessing.

## Required reading
Before substantial work, read:
1. `docs/architecture.md`
2. `docs/features.md`
3. `docs/implemented-features.md`
4. `docs/protocol.md`
5. `docs/milestones.md`
6. `docs/decisions.md`
