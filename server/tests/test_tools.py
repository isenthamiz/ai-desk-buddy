"""Unit tests for deterministic timer tools."""

import json

import pytest

from aideskbuddy.timer import TimerService
from aideskbuddy.tools import ToolRegistry


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
