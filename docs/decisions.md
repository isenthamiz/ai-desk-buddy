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
