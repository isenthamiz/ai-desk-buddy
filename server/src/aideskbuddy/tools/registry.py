"""Small explicit registry for deterministic actions."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, PositiveInt, ValidationError

from aideskbuddy.ai import ToolDefinition
from aideskbuddy.protocol import (
    BuddyState,
    ServerMessage,
    StateChanged,
    TimerCancelled,
    TimerStarted,
)
from aideskbuddy.timer import TimerService


class SetTimerArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    duration_seconds: PositiveInt


class NoArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True, slots=True)
class ToolResult:
    output: str
    messages: tuple[ServerMessage, ...] = ()


class ToolRegistry:
    """Expose timer actions to an AI provider and execute them safely."""

    def __init__(self, timer: TimerService) -> None:
        self._timer = timer

    @property
    def definitions(self) -> tuple[ToolDefinition, ...]:
        return (
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
        )

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
        except ValidationError as exc:
            return self._result(ok=False, error=str(exc))
        return self._result(ok=False, error=f"unknown tool: {name}")

    @staticmethod
    def _result(*, ok: bool, error: str) -> ToolResult:
        return ToolResult(output=json.dumps({"ok": ok, "error": error}))
