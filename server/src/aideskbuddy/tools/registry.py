"""Small explicit registry for deterministic actions."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, ValidationError, field_validator

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
from aideskbuddy.reminder import ReminderService


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
    ) -> None:
        self._timer = timer
        self._reminders = reminders
        self._device_id = device_id

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
                reminder = self._reminders.create(
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
                reminder = self._reminders.create_in(
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
                if not self._reminders.cancel(
                    self._required_device_id(), parsed.reminder_id
                ):
                    return self._result(ok=False, error="pending reminder not found")
                return ToolResult(
                    output=json.dumps({"ok": True, "reminderId": parsed.reminder_id}),
                    messages=(ReminderCancelled(reminderId=parsed.reminder_id),),
                )
        except ValidationError as exc:
            return self._result(ok=False, error=str(exc))
        return self._result(ok=False, error=f"unknown tool: {name}")

    @staticmethod
    def _result(*, ok: bool, error: str) -> ToolResult:
        return ToolResult(output=json.dumps({"ok": ok, "error": error}))

    def _required_device_id(self) -> str:
        if self._device_id is None:
            raise ValueError("device id is required for reminder tools")
        return self._device_id
