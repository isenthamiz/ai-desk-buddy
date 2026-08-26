"""Unit tests for deterministic timer tools."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from aideskbuddy.timer import TimerService
from aideskbuddy.tools import ToolRegistry
from aideskbuddy.reminder import ReminderService, SQLiteReminderRepository
from aideskbuddy.weather import WeatherProviderError, WeatherReport, WeatherService


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


@pytest.mark.asyncio
async def test_get_weather_tool_returns_structured_report() -> None:
    async def complete() -> None:
        pass

    class FakeWeatherProvider:
        async def get_weather(self, period):
            return WeatherReport(
                location="Dublin",
                period=period,
                date="2026-08-26",
                condition="partly cloudy",
                current_temperature_c=15.2,
                apparent_temperature_c=14.1,
                minimum_temperature_c=10.2,
                maximum_temperature_c=18.4,
                precipitation_probability_percent=70,
                precipitation_sum_mm=2.8,
                maximum_wind_speed_kmh=25.0,
            )

    timer = TimerService(complete)
    tools = ToolRegistry(timer, weather=WeatherService(FakeWeatherProvider()))

    result = await tools.execute("get_weather", {"period": "today"})
    output = json.loads(result.output)

    assert output["ok"] is True
    assert output["location"] == "Dublin"
    assert output["precipitation_probability_percent"] == 70
    assert result.messages == ()
    await timer.close()


@pytest.mark.asyncio
async def test_get_weather_tool_handles_provider_failure() -> None:
    async def complete() -> None:
        pass

    class FailingWeatherProvider:
        async def get_weather(self, _period):
            raise WeatherProviderError("network failed")

    timer = TimerService(complete)
    tools = ToolRegistry(timer, weather=WeatherService(FailingWeatherProvider()))

    result = await tools.execute("get_weather", {"period": "now"})

    assert json.loads(result.output) == {
        "ok": False,
        "error": "weather service unavailable",
    }
    await timer.close()
