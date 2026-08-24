"""WebSocket device boundary integration tests."""

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from aideskbuddy.main import create_app


def test_device_connects_and_exchanges_events_and_reactions() -> None:
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/device") as websocket:
            websocket.send_json(
                {
                    "type": "DEVICE_CONNECTED",
                    "deviceId": "simulator-001",
                    "deviceType": "SIMULATOR",
                }
            )
            assert websocket.receive_json() == {
                "type": "STATE_CHANGED",
                "state": "IDLE",
            }
            assert app.state.sessions.get("simulator-001") is not None

            websocket.send_json({"type": "BUTTON_PRESSED", "button": "ACTION"})
            assert websocket.receive_json() == {
                "type": "STATE_CHANGED",
                "state": "LISTENING",
            }

            websocket.send_json({"type": "PRESENCE_CHANGED", "present": False})
            assert websocket.receive_json() == {
                "type": "STATE_CHANGED",
                "state": "SLEEPING",
            }

            websocket.send_json(
                {"type": "USER_TEXT", "text": "Hello", "requestId": "req-1"}
            )
            assert websocket.receive_json() == {
                "type": "DISPLAY_TEXT",
                "text": "Echo: Hello",
                "requestId": "req-1",
            }
            assert websocket.receive_json() == {
                "type": "SPEAK",
                "text": "Echo: Hello",
                "requestId": "req-1",
            }

        assert len(app.state.sessions) == 0


def test_invalid_message_after_handshake_is_ignored() -> None:
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/device") as websocket:
            websocket.send_json(
                {
                    "type": "DEVICE_CONNECTED",
                    "deviceId": "simulator-001",
                    "deviceType": "SIMULATOR",
                }
            )
            websocket.receive_json()
            websocket.send_json({"type": "UNKNOWN"})
            websocket.send_json({"type": "PRESENCE_CHANGED", "present": True})

            assert websocket.receive_json() == {
                "type": "STATE_CHANGED",
                "state": "IDLE",
            }


def test_connection_requires_device_handshake() -> None:
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/device") as websocket:
            websocket.send_json({"type": "USER_TEXT", "text": "Too early"})

            try:
                websocket.receive_json()
            except WebSocketDisconnect as exc:
                assert exc.code == 1008
            else:
                raise AssertionError("server did not reject missing device handshake")
