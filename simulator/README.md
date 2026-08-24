# AI Desk Buddy Simulator

This package is the desktop representation of the future Desk Buddy display.
The simulator currently contains:

- a configurable virtual display
- a 240×240 circular display matching the target hardware
- two rendered eyes
- eight manually selectable Desk Buddy states
- state-specific expressions and lightweight animations
- calm, randomly timed blinking and subtle idle movement

It intentionally has no hardware, buzzer, or audio support. Its WebSocket client
uses the same public device protocol intended for the ESP32.

## Run locally

From this directory, install the package and development dependencies with
[`uv`](https://docs.astral.sh/uv/):

```bash
uv sync
uv run buddy-simulator
```

Press Escape or close the window to exit.

Press `?` or F1 to show or hide the command helper.

By default, the simulator connects to:

```text
ws://127.0.0.1:8000/ws/device
```

Start the FastAPI server first from another terminal. The display shows a green
`CONNECTED` indicator after the `DEVICE_CONNECTED` handshake succeeds. If the
server is unavailable, the simulator keeps running and retries automatically.

Run without networking when working only on visuals:

```bash
uv run buddy-simulator --offline
```

Choose the initial state from the command line:

```bash
uv run buddy-simulator --state THINKING
```

Switch states while the simulator is running:

| Key | State |
| --- | --- |
| `1` | `IDLE` |
| `2` | `LISTENING` |
| `3` | `THINKING` |
| `4` | `SPEAKING` |
| `5` | `TIMER` |
| `6` | `NOTIFICATION` |
| `7` | `SLEEPING` |
| `8` | `ERROR` |

## Device protocol controls

These controls act like future physical-device inputs. They send documented
protocol events to the server; the face reacts only after receiving a server
command.

| Key | Device event |
| --- | --- |
| `F` | Send `BUTTON_PRESSED` with button `ACTION` |
| `P` | Toggle and send `PRESENCE_CHANGED` |
| `T` | Enter text and send `USER_TEXT` |

For text input, type a message and press Enter. Backspace edits and Escape
cancels. Sent and received protocol messages are logged in the terminal.

Connect to a different server or use a different simulated device ID:

```bash
uv run buddy-simulator \
  --server-url ws://127.0.0.1:8000/ws/device \
  --device-id simulator-002
```

## Timer controls

When connected, press `T` and ask Buddy to set or cancel a timer. These AI tool
actions are owned by the backend and reflected through timer protocol messages.
The controls below remain available for offline display testing.

The timer starts at 60 seconds by default. While it is inactive:

- Up Arrow adds 10 seconds.
- Down Arrow removes 10 seconds, down to a minimum of one second.
- Enter starts the timer.

Adjusting the duration opens the `TIMER` preview so the selected value is
visible before starting.

While the timer is running:

- Space pauses or resumes it.
- `C` cancels it and returns to `IDLE`.

The simulator enters `TIMER` while the countdown is active. At completion it
shows a temporary `Timer complete!` notification, then returns to `IDLE`.

Set a different initial duration from the command line:

```bash
uv run buddy-simulator --timer-duration 15
```

## Notification controls

Press `N` to open the notification text-entry overlay. Type any message and
press Enter to show it. Backspace edits the message; Escape closes the overlay
without sending.

The simulator remembers the state that was active before the notification,
shows the message with the notification expression, and restores the saved
state after 2.5 seconds. A notification shown over a running timer returns to
the active timer.

Configure the display period when launching:

```bash
uv run buddy-simulator --notification-duration 5
```

## Face animation controls

The reusable face controller supports expressions, blinking, and smoothly
interpolated gaze targets. Use these developer keys while the simulator runs:

Each expression produces a coordinated `FacePose` containing pixel-phosphor
eye geometry, eye tilt, mouth shape, mouth openness, and subtle face movement.
The renderer consumes the pose without putting animation behavior into the
application or state machine.

| Key | Face action |
| --- | --- |
| `B` | Blink |
| `H` | Happy expression |
| `A` | Look left |
| `D` | Look right |
| `W` | Look up |
| `S` | Look down |
| `X` | Return gaze to center |

State keys still select the listening, thinking, sleeping, surprised
notification, and error expressions. Selecting a state restores the expression
associated with that state.

Run the tests with:

```bash
uv run pytest
```
