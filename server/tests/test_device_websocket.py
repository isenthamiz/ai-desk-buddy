"""WebSocket device boundary integration tests."""

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from collections.abc import Sequence

from aideskbuddy.ai import (
    AIProviderError,
    ConversationMessage,
    ToolDefinition,
    ToolExecutor,
)
from aideskbuddy.main import create_app


class FakeAIProvider:
    def __init__(self) -> None:
        self.calls: list[list[ConversationMessage]] = []

    async def reply(
        self,
        messages: Sequence[ConversationMessage],
        *,
        tools: Sequence[ToolDefinition] = (),
        execute_tool: ToolExecutor | None = None,
    ) -> str:
        del tools, execute_tool
        self.calls.append(list(messages))
        return "Hi! How can I help?"


class FailingAIProvider:
    async def reply(
        self,
        messages: Sequence[ConversationMessage],
        *,
        tools: Sequence[ToolDefinition] = (),
        execute_tool: ToolExecutor | None = None,
    ) -> str:
        del messages, tools, execute_tool
        raise AIProviderError("provider unavailable")


class TimerAIProvider:
    async def reply(
        self,
        messages: Sequence[ConversationMessage],
        *,
        tools: Sequence[ToolDefinition] = (),
        execute_tool: ToolExecutor | None = None,
    ) -> str:
        del messages
        assert {tool.name for tool in tools} == {"set_timer", "cancel_timer"}
        assert execute_tool is not None
        await execute_tool("set_timer", {"duration_seconds": 1})
        return "Timer set for one second."


def test_device_connects_and_exchanges_events_and_reactions() -> None:
    provider = FakeAIProvider()
    app = create_app(ai_provider=provider)
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
                "type": "STATE_CHANGED",
                "state": "THINKING",
                "requestId": "req-1",
            }
            assert websocket.receive_json() == {
                "type": "STATE_CHANGED",
                "state": "SPEAKING",
                "requestId": "req-1",
            }
            assert websocket.receive_json() == {
                "type": "DISPLAY_TEXT",
                "text": "Hi! How can I help?",
                "requestId": "req-1",
            }
            assert websocket.receive_json() == {
                "type": "SPEAK",
                "text": "Hi! How can I help?",
                "requestId": "req-1",
            }
            assert websocket.receive_json() == {
                "type": "STATE_CHANGED",
                "state": "IDLE",
                "requestId": "req-1",
            }

            websocket.send_json({"type": "USER_TEXT", "text": "Remember me"})
            for _ in range(5):
                websocket.receive_json()

            assert provider.calls[1] == [
                ConversationMessage(role="user", content="Hello"),
                ConversationMessage(role="assistant", content="Hi! How can I help?"),
                ConversationMessage(role="user", content="Remember me"),
            ]

        assert len(app.state.sessions) == 0


def test_ai_provider_error_is_reported_and_connection_stays_usable() -> None:
    app = create_app(ai_provider=FailingAIProvider())
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
            websocket.send_json({"type": "USER_TEXT", "text": "Hello"})

            assert websocket.receive_json()["state"] == "THINKING"
            assert websocket.receive_json()["state"] == "ERROR"
            assert websocket.receive_json()["type"] == "DISPLAY_TEXT"
            assert websocket.receive_json()["type"] == "SPEAK"
            assert websocket.receive_json()["state"] == "IDLE"

            websocket.send_json({"type": "PRESENCE_CHANGED", "present": True})
            assert websocket.receive_json()["state"] == "IDLE"


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


def test_ai_tool_starts_timer_and_backend_reports_completion() -> None:
    app = create_app(ai_provider=TimerAIProvider())
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
            websocket.send_json({"type": "USER_TEXT", "text": "Set a timer"})

            assert websocket.receive_json()["state"] == "THINKING"
            assert websocket.receive_json() == {
                "type": "TIMER_STARTED",
                "durationSeconds": 1,
            }
            assert websocket.receive_json()["state"] == "TIMER"
            assert websocket.receive_json()["state"] == "SPEAKING"
            assert websocket.receive_json()["type"] == "DISPLAY_TEXT"
            assert websocket.receive_json()["type"] == "SPEAK"
            assert websocket.receive_json()["state"] == "TIMER"

            assert websocket.receive_json()["type"] == "TIMER_COMPLETED"
            assert websocket.receive_json()["state"] == "ALERT"
            assert websocket.receive_json()["type"] == "DISPLAY_TEXT"
            assert websocket.receive_json()["type"] == "SPEAK"
            assert websocket.receive_json()["state"] == "IDLE"
