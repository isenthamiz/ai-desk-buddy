"""Pydantic models for protocol v0.1."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, StrictBool, field_validator


class ProtocolMessage(BaseModel):
    """Fields shared by all device protocol messages."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    request_id: str | None = Field(default=None, alias="requestId")


class BuddyState(StrEnum):
    SLEEPING = "SLEEPING"
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    TIMER = "TIMER"
    ALERT = "ALERT"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"


class DeviceConnected(ProtocolMessage):
    type: Literal["DEVICE_CONNECTED"] = "DEVICE_CONNECTED"
    device_id: str = Field(alias="deviceId", min_length=1)
    device_type: Literal["SIMULATOR", "ESP32"] = Field(alias="deviceType")


class UserText(ProtocolMessage):
    type: Literal["USER_TEXT"] = "USER_TEXT"
    text: str = Field(min_length=1)


class ButtonPressed(ProtocolMessage):
    type: Literal["BUTTON_PRESSED"] = "BUTTON_PRESSED"
    button: str = Field(min_length=1)
    duration_seconds: int | None = Field(
        default=None, alias="durationSeconds", gt=0, le=86_400
    )


class PresenceChanged(ProtocolMessage):
    type: Literal["PRESENCE_CHANGED"] = "PRESENCE_CHANGED"
    present: StrictBool


class CreateReminder(ProtocolMessage):
    type: Literal["CREATE_REMINDER"] = "CREATE_REMINDER"
    text: str = Field(min_length=1, max_length=500)
    due_at: datetime = Field(alias="dueAt")

    @field_validator("due_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dueAt must include a UTC offset")
        return value


class CancelReminder(ProtocolMessage):
    type: Literal["CANCEL_REMINDER"] = "CANCEL_REMINDER"
    reminder_id: str = Field(alias="reminderId", min_length=1)


class StateChanged(ProtocolMessage):
    type: Literal["STATE_CHANGED"] = "STATE_CHANGED"
    state: BuddyState


class DisplayText(ProtocolMessage):
    type: Literal["DISPLAY_TEXT"] = "DISPLAY_TEXT"
    text: str


class Speak(ProtocolMessage):
    type: Literal["SPEAK"] = "SPEAK"
    text: str


class TimerStarted(ProtocolMessage):
    type: Literal["TIMER_STARTED"] = "TIMER_STARTED"
    duration_seconds: PositiveInt = Field(alias="durationSeconds")


class TimerCancelled(ProtocolMessage):
    type: Literal["TIMER_CANCELLED"] = "TIMER_CANCELLED"


class TimerCompleted(ProtocolMessage):
    type: Literal["TIMER_COMPLETED"] = "TIMER_COMPLETED"


class ReminderCreated(ProtocolMessage):
    type: Literal["REMINDER_CREATED"] = "REMINDER_CREATED"
    reminder_id: str = Field(alias="reminderId")
    text: str
    due_at: datetime = Field(alias="dueAt")


class ReminderCancelled(ProtocolMessage):
    type: Literal["REMINDER_CANCELLED"] = "REMINDER_CANCELLED"
    reminder_id: str = Field(alias="reminderId")


class ReminderDue(ProtocolMessage):
    type: Literal["REMINDER_DUE"] = "REMINDER_DUE"
    reminder_id: str = Field(alias="reminderId")
    text: str
    due_at: datetime = Field(alias="dueAt")


DeviceMessage = (
    DeviceConnected | UserText | ButtonPressed | PresenceChanged | CreateReminder | CancelReminder
)
ServerMessage = (
    StateChanged | DisplayText | Speak | TimerStarted | TimerCancelled | TimerCompleted
    | ReminderCreated | ReminderCancelled | ReminderDue
)
