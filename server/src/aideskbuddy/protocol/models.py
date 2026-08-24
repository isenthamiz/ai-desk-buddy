"""Pydantic models for protocol v0.1."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, StrictBool


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
    device_type: Literal["SIMULATOR"] = Field(alias="deviceType")


class UserText(ProtocolMessage):
    type: Literal["USER_TEXT"] = "USER_TEXT"
    text: str = Field(min_length=1)


class ButtonPressed(ProtocolMessage):
    type: Literal["BUTTON_PRESSED"] = "BUTTON_PRESSED"
    button: str = Field(min_length=1)


class PresenceChanged(ProtocolMessage):
    type: Literal["PRESENCE_CHANGED"] = "PRESENCE_CHANGED"
    present: StrictBool


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


DeviceMessage = DeviceConnected | UserText | ButtonPressed | PresenceChanged
ServerMessage = (
    StateChanged | DisplayText | Speak | TimerStarted | TimerCancelled | TimerCompleted
)
