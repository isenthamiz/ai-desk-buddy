# Device ↔ Backend Protocol

## Status
**Draft v0.2**

This protocol is intentionally small. Milestone 1 only needs enough messages to prove simulator ↔ FastAPI communication. Later milestones can extend it.

## Transport
Primary transport: WebSocket.

Initial endpoint recommendation:

```text
/ws/device
```

The exact endpoint can be adjusted during implementation, but changes should be reflected here.

## Envelope
Use JSON messages.

Recommended common fields:

```json
{
  "type": "MESSAGE_TYPE",
  "requestId": "optional-correlation-id"
}
```

`requestId` is optional initially and useful when a response/action needs correlation.

## Device → Server messages

### DEVICE_CONNECTED
Identifies a simulator/device after connecting.

```json
{
  "type": "DEVICE_CONNECTED",
  "deviceId": "simulator-001",
  "deviceType": "SIMULATOR"
}
```

Possible future device type: `ESP32`.

### USER_TEXT
Temporary/diagnostic text input used by the simulator before voice is implemented.

```json
{
  "type": "USER_TEXT",
  "text": "Hello"
}
```

For AI conversation, the server responds with the existing message types in this
order: `STATE_CHANGED(THINKING)`, `STATE_CHANGED(SPEAKING)`, `DISPLAY_TEXT`,
`SPEAK`, then `STATE_CHANGED(IDLE)`. Provider failures use
`STATE_CHANGED(ERROR)`, a short `DISPLAY_TEXT`/`SPEAK` apology, then return to
`STATE_CHANGED(IDLE)`.

### BUTTON_PRESSED

```json
{
  "type": "BUTTON_PRESSED",
  "button": "ACTION"
}
```

Button names are intentionally not fully defined until hardware/control behavior is finalized.

### PRESENCE_CHANGED

```json
{
  "type": "PRESENCE_CHANGED",
  "present": true
}
```

## Server → Device messages

### STATE_CHANGED

```json
{
  "type": "STATE_CHANGED",
  "state": "IDLE"
}
```

Initial state values:

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

### DISPLAY_TEXT
Useful for simulator/testing and simple display output.

```json
{
  "type": "DISPLAY_TEXT",
  "text": "Hello!"
}
```

### SPEAK
Represents text that should eventually be spoken. Before audio exists, the simulator can simply print it.

```json
{
  "type": "SPEAK",
  "text": "Your timer has finished."
}
```

### TIMER_STARTED
Starts or replaces the device's presentation of the backend-owned countdown.
Milestone 3 supports one active timer per connected device; a second timer request
fails until the active timer is cancelled or completes.

```json
{
  "type": "TIMER_STARTED",
  "durationSeconds": 300
}
```

The server follows this with `STATE_CHANGED(TIMER)`. The device may render the
countdown locally, but the backend remains authoritative for cancellation and expiry.

### TIMER_CANCELLED

```json
{
  "type": "TIMER_CANCELLED"
}
```

The server follows this with `STATE_CHANGED(IDLE)`.

### TIMER_COMPLETED

```json
{
  "type": "TIMER_COMPLETED"
}
```

On expiry the server sends `TIMER_COMPLETED`, `STATE_CHANGED(ALERT)`, a short
`DISPLAY_TEXT` and `SPEAK` alert, then `STATE_CHANGED(IDLE)`.

## Validation
On the Python backend:
- use Pydantic models for message validation
- parse message type explicitly
- reject or safely log invalid payloads
- keep JSON parsing/validation separate from business logic

## Future messages
Do not implement these merely because they are listed here. They are likely future additions:
- audio stream/start/stop messages
- timer countdown updates (only if later needed)
- animation commands
- volume changes
- device configuration
- heartbeat/health messages
- errors with structured codes
- capability negotiation

## Compatibility rules
- Unknown message types should fail safely and be logged.
- Message parsing should be isolated from business logic.
- Additive fields should be preferred over breaking changes.
- Protocol changes must update this document and relevant tests.
- The simulator and ESP32 should use the same protocol semantics.
