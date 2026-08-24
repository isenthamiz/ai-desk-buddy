"""Public device/backend protocol."""

from aideskbuddy.protocol.models import (
    BuddyState,
    ButtonPressed,
    DeviceConnected,
    DeviceMessage,
    DisplayText,
    PresenceChanged,
    ServerMessage,
    Speak,
    StateChanged,
    UserText,
)
from aideskbuddy.protocol.parser import ProtocolMessageError, parse_device_message

__all__ = [
    "BuddyState",
    "ButtonPressed",
    "DeviceConnected",
    "DeviceMessage",
    "DisplayText",
    "PresenceChanged",
    "ProtocolMessageError",
    "ServerMessage",
    "Speak",
    "StateChanged",
    "UserText",
    "parse_device_message",
]
