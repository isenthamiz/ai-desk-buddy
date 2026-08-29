"""Small explicit registry for deterministic actions."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    ValidationError,
    field_validator,
    model_validator,
)

from aideskbuddy.ai import ToolDefinition
from aideskbuddy.protocol import (
    BuddyState,
    ReminderCancelled,
    ReminderCreated,
    ServerMessage,
    StateChanged,
    TimerCancelled,
    TimerStarted,
)
from aideskbuddy.timer import TimerService
from aideskbuddy.todoist import TodoistProviderError, TodoistService
from aideskbuddy.reminder import ReminderService
from aideskbuddy.weather import WeatherProviderError, WeatherService


class SetTimerArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    duration_seconds: PositiveInt


class NoArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateReminderArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=500)
    due_at: datetime

    @field_validator("due_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("due_at must include a UTC offset")
        return value


class CreateRelativeReminderArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=500)
    delay_seconds: PositiveInt


class CancelReminderArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reminder_id: str = Field(min_length=1)


class GetWeatherArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period: Literal["now", "today", "tomorrow"]


class CreateTodoistTaskArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=500)
    due_date: date | None
    due_at: datetime | None

    @model_validator(mode="after")
    def validate_due_fields(self) -> "CreateTodoistTaskArguments":
        if self.due_date is not None and self.due_at is not None:
            raise ValueError("provide due_date or due_at, not both")
        if self.due_at is not None and (
            self.due_at.tzinfo is None or self.due_at.utcoffset() is None
        ):
            raise ValueError("due_at must include a UTC offset")
        return self


class ListTodoistTasksArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period: Literal["today", "overdue", "upcoming"]


class CompleteTodoistTaskArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(min_length=1, max_length=100)


@dataclass(frozen=True, slots=True)
class ToolResult:
    output: str
    messages: tuple[ServerMessage, ...] = ()


class ToolRegistry:
    """Expose timer actions to an AI provider and execute them safely."""

    def __init__(
        self,
        timer: TimerService,
        reminders: ReminderService | None = None,
        device_id: str | None = None,
        weather: WeatherService | None = None,
        todoist: TodoistService | None = None,
    ) -> None:
        self._timer = timer
        self._reminders = reminders
        self._device_id = device_id
        self._weather = weather
        self._todoist = todoist

    @property
    def definitions(self) -> tuple[ToolDefinition, ...]:
        definitions = [
            ToolDefinition(
                name="set_timer",
                description="Start a countdown timer for the requested whole seconds.",
                parameters=SetTimerArguments.model_json_schema(),
            ),
            ToolDefinition(
                name="cancel_timer",
                description="Cancel the currently active timer.",
                parameters=NoArguments.model_json_schema(),
            ),
        ]
        if self._reminders is not None:
            definitions.extend(
                [
                    ToolDefinition(
                        name="create_relative_reminder",
                        description=(
                            "Create a one-shot reminder after a relative delay. Use "
                            "this for requests such as 'in one minute' or 'in two hours'."
                        ),
                        parameters=CreateRelativeReminderArguments.model_json_schema(),
                    ),
                    ToolDefinition(
                        name="create_reminder",
                        description=(
                            "Create a one-shot reminder. Use an ISO 8601 due_at with "
                            "an explicit UTC offset."
                        ),
                        parameters=CreateReminderArguments.model_json_schema(),
                    ),
                    ToolDefinition(
                        name="cancel_reminder",
                        description="Cancel a pending reminder by its reminder_id.",
                        parameters=CancelReminderArguments.model_json_schema(),
                    ),
                ]
            )
        if self._weather is not None:
            definitions.append(
                ToolDefinition(
                    name="get_weather",
                    description=(
                        "Get current, today's, or tomorrow's weather for Buddy's "
                        "configured location. Use this for all weather questions."
                    ),
                    parameters=GetWeatherArguments.model_json_schema(),
                )
            )
        if self._todoist is not None:
            definitions.extend(
                [
                    ToolDefinition(
                        name="create_todoist_task",
                        description=(
                            "Create a Todoist Inbox task. Pass a date-only due_date, "
                            "a timezone-aware due_at, or null for both when not given."
                        ),
                        parameters=CreateTodoistTaskArguments.model_json_schema(),
                    ),
                    ToolDefinition(
                        name="list_todoist_tasks",
                        description=(
                            "List up to five active Todoist tasks for today, overdue, "
                            "or the upcoming seven days."
                        ),
                        parameters=ListTodoistTasksArguments.model_json_schema(),
                    ),
                    ToolDefinition(
                        name="complete_todoist_task",
                        description=(
                            "Complete a Todoist task using the exact task_id returned "
                            "by create_todoist_task or list_todoist_tasks."
                        ),
                        parameters=CompleteTodoistTaskArguments.model_json_schema(),
                    ),
                ]
            )
        return tuple(definitions)

    async def execute(self, name: str, arguments: Mapping[str, Any]) -> ToolResult:
        try:
            if name == "set_timer":
                parsed = SetTimerArguments.model_validate(arguments)
                if not self._timer.start(parsed.duration_seconds):
                    return self._result(ok=False, error="a timer is already active")
                return ToolResult(
                    output=json.dumps(
                        {"ok": True, "durationSeconds": parsed.duration_seconds}
                    ),
                    messages=(
                        TimerStarted(durationSeconds=parsed.duration_seconds),
                        StateChanged(state=BuddyState.TIMER),
                    ),
                )
            if name == "cancel_timer":
                NoArguments.model_validate(arguments)
                if not self._timer.cancel():
                    return self._result(ok=False, error="there is no active timer")
                return ToolResult(
                    output=json.dumps({"ok": True}),
                    messages=(
                        TimerCancelled(),
                        StateChanged(state=BuddyState.IDLE),
                    ),
                )
            if name == "create_reminder" and self._reminders is not None:
                parsed = CreateReminderArguments.model_validate(arguments)
                reminder = await self._reminders.create(
                    self._required_device_id(), parsed.text, parsed.due_at
                )
                return ToolResult(
                    output=json.dumps(
                        {
                            "ok": True,
                            "reminderId": reminder.id,
                            "dueAt": reminder.due_at.isoformat(),
                        }
                    ),
                    messages=(
                        ReminderCreated(
                            reminderId=reminder.id,
                            text=reminder.text,
                            dueAt=reminder.due_at,
                        ),
                    ),
                )
            if name == "create_relative_reminder" and self._reminders is not None:
                parsed = CreateRelativeReminderArguments.model_validate(arguments)
                reminder = await self._reminders.create_in(
                    self._required_device_id(), parsed.text, parsed.delay_seconds
                )
                return ToolResult(
                    output=json.dumps(
                        {
                            "ok": True,
                            "reminderId": reminder.id,
                            "dueAt": reminder.due_at.isoformat(),
                        }
                    ),
                    messages=(
                        ReminderCreated(
                            reminderId=reminder.id,
                            text=reminder.text,
                            dueAt=reminder.due_at,
                        ),
                    ),
                )
            if name == "cancel_reminder" and self._reminders is not None:
                parsed = CancelReminderArguments.model_validate(arguments)
                if not await self._reminders.cancel(
                    self._required_device_id(), parsed.reminder_id
                ):
                    return self._result(ok=False, error="pending reminder not found")
                return ToolResult(
                    output=json.dumps({"ok": True, "reminderId": parsed.reminder_id}),
                    messages=(ReminderCancelled(reminderId=parsed.reminder_id),),
                )
            if name == "get_weather" and self._weather is not None:
                parsed = GetWeatherArguments.model_validate(arguments)
                report = await self._weather.get_weather(parsed.period)
                return ToolResult(
                    output=json.dumps(
                        {"ok": True, **report.model_dump(mode="json")}
                    )
                )
            if name == "create_todoist_task" and self._todoist is not None:
                parsed = CreateTodoistTaskArguments.model_validate(arguments)
                task = await self._todoist.create_task(
                    parsed.content,
                    due_date=parsed.due_date,
                    due_at=parsed.due_at,
                )
                return ToolResult(
                    output=json.dumps(
                        {"ok": True, "task": task.model_dump(mode="json")}
                    )
                )
            if name == "list_todoist_tasks" and self._todoist is not None:
                parsed = ListTodoistTasksArguments.model_validate(arguments)
                tasks = await self._todoist.list_tasks(parsed.period)
                return ToolResult(
                    output=json.dumps(
                        {
                            "ok": True,
                            "period": parsed.period,
                            "count": len(tasks),
                            "tasks": [task.model_dump(mode="json") for task in tasks],
                        }
                    )
                )
            if name == "complete_todoist_task" and self._todoist is not None:
                parsed = CompleteTodoistTaskArguments.model_validate(arguments)
                await self._todoist.complete_task(parsed.task_id)
                return ToolResult(
                    output=json.dumps({"ok": True, "taskId": parsed.task_id})
                )
        except ValidationError as exc:
            return self._result(ok=False, error=str(exc))
        except WeatherProviderError:
            return self._result(ok=False, error="weather service unavailable")
        except TodoistProviderError as exc:
            return self._result(ok=False, error=str(exc))
        return self._result(ok=False, error=f"unknown tool: {name}")

    @staticmethod
    def _result(*, ok: bool, error: str) -> ToolResult:
        return ToolResult(output=json.dumps({"ok": ok, "error": error}))

    def _required_device_id(self) -> str:
        if self._device_id is None:
            raise ValueError("device id is required for reminder tools")
        return self._device_id
