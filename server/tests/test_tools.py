"""Unit tests for deterministic timer tools."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from aideskbuddy.timer import TimerService
from aideskbuddy.todoist import TodoistService, TodoistTask
from aideskbuddy.tools import ToolRegistry
from aideskbuddy.reminder import InMemoryReminderRepository, ReminderService
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
        InMemoryReminderRepository(), notify
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
        InMemoryReminderRepository(), notify
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


@pytest.mark.asyncio
async def test_todoist_tools_create_list_and_complete_tasks() -> None:
    async def complete() -> None:
        pass

    class FakeTodoistProvider:
        def __init__(self) -> None:
            self.completed_id: str | None = None

        async def create_task(self, content, *, due_date=None, due_at=None):
            assert due_date is None
            assert due_at == datetime.fromisoformat("2026-08-27T09:00:00+01:00")
            return TodoistTask(id="task-1", content=content, due_date="2026-08-27")

        async def list_tasks(self, period, *, limit):
            assert period == "today"
            assert limit == 5
            return [TodoistTask(id="task-1", content="Submit expenses")]

        async def complete_task(self, task_id):
            self.completed_id = task_id

    provider = FakeTodoistProvider()
    timer = TimerService(complete)
    tools = ToolRegistry(timer, todoist=TodoistService(provider))

    assert {definition.name for definition in tools.definitions} == {
        "set_timer",
        "cancel_timer",
        "create_todoist_task",
        "list_todoist_tasks",
        "complete_todoist_task",
    }
    created = await tools.execute(
        "create_todoist_task",
        {
            "content": "Submit expenses",
            "due_date": None,
            "due_at": "2026-08-27T09:00:00+01:00",
        },
    )
    listed = await tools.execute("list_todoist_tasks", {"period": "today"})
    completed = await tools.execute(
        "complete_todoist_task", {"task_id": "task-1"}
    )

    assert json.loads(created.output)["task"]["id"] == "task-1"
    assert json.loads(listed.output)["count"] == 1
    assert json.loads(completed.output) == {"ok": True, "taskId": "task-1"}
    assert provider.completed_id == "task-1"
    await timer.close()


@pytest.mark.asyncio
async def test_todoist_create_task_validates_due_fields() -> None:
    async def complete() -> None:
        pass

    class UnusedProvider:
        async def create_task(self, *_args, **_kwargs):
            raise AssertionError("invalid arguments should not reach provider")

        async def list_tasks(self, *_args, **_kwargs):
            raise AssertionError("not used")

        async def complete_task(self, *_args, **_kwargs):
            raise AssertionError("not used")

    timer = TimerService(complete)
    tools = ToolRegistry(timer, todoist=TodoistService(UnusedProvider()))

    result = await tools.execute(
        "create_todoist_task",
        {
            "content": "Conflicting due fields",
            "due_date": "2026-08-27",
            "due_at": "2026-08-27T09:00:00+01:00",
        },
    )

    assert json.loads(result.output)["ok"] is False
    await timer.close()
