"""Unit tests for deterministic timer tools."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from aideskbuddy.timer import TimerService
from aideskbuddy.tools import ToolRegistry
from aideskbuddy.reminder import ReminderService, SQLiteReminderRepository


@pytest.mark.asyncio
async def test_set_and_cancel_timer_tools() -> None:
    async def complete() -> None:
        pass

    timer = TimerService(complete)
    tools = ToolRegistry(timer)

    started = await tools.execute("set_timer", {"duration_seconds": 30})
    assert json.loads(started.output) == {"ok": True, "durationSeconds": 30}
    assert [message.type for message in started.messages] == [
        "TIMER_STARTED",
        "STATE_CHANGED",
    ]
    assert timer.is_active

    duplicate = await tools.execute("set_timer", {"duration_seconds": 10})
    assert json.loads(duplicate.output)["ok"] is False

    cancelled = await tools.execute("cancel_timer", {})
    assert json.loads(cancelled.output) == {"ok": True}
    assert [message.type for message in cancelled.messages] == [
        "TIMER_CANCELLED",
        "STATE_CHANGED",
    ]
    assert not timer.is_active
    await timer.close()


@pytest.mark.asyncio
async def test_tool_arguments_are_validated() -> None:
    async def complete() -> None:
        pass

    timer = TimerService(complete)
    tools = ToolRegistry(timer)

    invalid = await tools.execute("set_timer", {"duration_seconds": 0})
    unknown = await tools.execute("unknown", {})

    assert json.loads(invalid.output)["ok"] is False
    assert json.loads(unknown.output)["error"] == "unknown tool: unknown"


@pytest.mark.asyncio
async def test_create_and_cancel_reminder_tools(tmp_path) -> None:
    async def complete() -> None:
        pass

    async def notify(_reminder) -> bool:
        return True

    timer = TimerService(complete)
    reminders = ReminderService(
        SQLiteReminderRepository(tmp_path / "buddy.db"), notify
    )
    tools = ToolRegistry(timer, reminders, "simulator-001")
    due_at = datetime.now(UTC) + timedelta(hours=1)

    created = await tools.execute(
        "create_reminder",
        {"text": "Join the design review", "due_at": due_at.isoformat()},
    )
    created_output = json.loads(created.output)
    assert created_output["ok"] is True
    assert [message.type for message in created.messages] == ["REMINDER_CREATED"]

    cancelled = await tools.execute(
        "cancel_reminder", {"reminder_id": created_output["reminderId"]}
    )
    assert json.loads(cancelled.output)["ok"] is True
    assert [message.type for message in cancelled.messages] == ["REMINDER_CANCELLED"]
    await timer.close()


@pytest.mark.asyncio
async def test_relative_reminder_tool_uses_delay_seconds(tmp_path) -> None:
    async def complete() -> None:
        pass

    async def notify(_reminder) -> bool:
        return True

    timer = TimerService(complete)
    reminders = ReminderService(
        SQLiteReminderRepository(tmp_path / "buddy.db"), notify
    )
    tools = ToolRegistry(timer, reminders, "simulator-001")

    created = await tools.execute(
        "create_relative_reminder",
        {"text": "Stretch", "delay_seconds": 60},
    )

    assert json.loads(created.output)["ok"] is True
    assert created.messages[0].type == "REMINDER_CREATED"
    await timer.close()
