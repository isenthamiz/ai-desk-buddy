"""Integration tests for the browser-facing Buddy control API."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from aideskbuddy.ai import ConversationMessage, ToolDefinition, ToolExecutor
from aideskbuddy.main import create_app
from aideskbuddy.reminder import InMemoryReminderRepository


class ControlAIProvider:
    async def reply(
        self,
        messages: Sequence[ConversationMessage],
        *,
        tools: Sequence[ToolDefinition] = (),
        execute_tool: ToolExecutor | None = None,
    ) -> str:
        del tools, execute_tool
        return f"You said: {messages[-1].content}"


def connect_simulator(client: TestClient):
    websocket = client.websocket_connect("/ws/device")
    connection = websocket.__enter__()
    connection.send_json(
        {
            "type": "DEVICE_CONNECTED",
            "deviceId": "simulator-001",
            "deviceType": "SIMULATOR",
        }
    )
    assert connection.receive_json()["state"] == "IDLE"
    return websocket, connection


def test_offline_control_status_is_available_without_embedded_page(tmp_path) -> None:
    app = create_app(reminder_repository=InMemoryReminderRepository())
    with TestClient(app) as client:
        page = client.get("/control")
        status = client.get("/api/control/status")

    assert page.status_code == 404
    assert status.json()["device"] == {
        "id": "simulator-001",
        "type": None,
        "connected": False,
        "state": "OFFLINE",
    }


def test_control_api_allows_configured_web_origin(tmp_path) -> None:
    app = create_app(
        reminder_repository=InMemoryReminderRepository(),
        control_allowed_origins=["http://localhost:8081"],
    )
    with TestClient(app) as client:
        response = client.options(
            "/api/control/status",
            headers={
                "Origin": "http://localhost:8081",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8081"


def test_control_timer_updates_connected_simulator(tmp_path) -> None:
    app = create_app(reminder_repository=InMemoryReminderRepository())
    with TestClient(app) as client:
        context, websocket = connect_simulator(client)
        try:
            started = client.post(
                "/api/control/timers", json={"durationSeconds": 60}
            )
            assert started.status_code == 201
            assert websocket.receive_json() == {
                "type": "TIMER_STARTED",
                "durationSeconds": 60,
            }
            assert websocket.receive_json()["state"] == "TIMER"
            assert client.get("/api/control/status").json()["timer"] == {
                "active": True,
                "durationSeconds": 60,
            }

            cancelled = client.delete("/api/control/timers/current")
            assert cancelled.status_code == 200
            assert websocket.receive_json()["type"] == "TIMER_CANCELLED"
            assert websocket.receive_json()["state"] == "IDLE"
        finally:
            context.__exit__(None, None, None)


def test_control_text_uses_conversation_and_device_flow(tmp_path) -> None:
    app = create_app(
        ai_provider=ControlAIProvider(), reminder_repository=InMemoryReminderRepository()
    )
    with TestClient(app) as client:
        context, websocket = connect_simulator(client)
        try:
            response = client.post(
                "/api/control/messages", json={"text": "Hello Buddy"}
            )
            assert response.status_code == 202
            messages = [websocket.receive_json() for _ in range(5)]
            assert [message["type"] for message in messages] == [
                "STATE_CHANGED",
                "STATE_CHANGED",
                "DISPLAY_TEXT",
                "SPEAK",
                "STATE_CHANGED",
            ]
            assert messages[2]["text"] == "You said: Hello Buddy"
        finally:
            context.__exit__(None, None, None)


def test_control_reminders_can_be_created_listed_and_cancelled(tmp_path) -> None:
    app = create_app(reminder_repository=InMemoryReminderRepository())
    due_at = datetime.now(UTC) + timedelta(hours=1)
    with TestClient(app) as client:
        created = client.post(
            "/api/control/reminders",
            json={"text": "Take a break", "dueAt": due_at.isoformat()},
        )
        assert created.status_code == 201
        reminder_id = created.json()["id"]

        listed = client.get("/api/control/reminders")
        assert [item["id"] for item in listed.json()["items"]] == [reminder_id]

        cancelled = client.delete(f"/api/control/reminders/{reminder_id}")
        assert cancelled.status_code == 200
        assert client.get("/api/control/reminders").json() == {"items": []}


def test_control_actions_require_connected_buddy(tmp_path) -> None:
    app = create_app(reminder_repository=InMemoryReminderRepository())
    with TestClient(app) as client:
        timer = client.post("/api/control/timers", json={"durationSeconds": 60})
        text = client.post("/api/control/messages", json={"text": "Hello"})

    assert timer.status_code == 409
    assert text.status_code == 409
