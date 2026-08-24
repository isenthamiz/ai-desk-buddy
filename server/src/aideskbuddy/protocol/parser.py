"""Explicit parsing for incoming protocol messages."""

import json
from collections.abc import Mapping

from pydantic import ValidationError

from aideskbuddy.protocol.models import (
    ButtonPressed,
    CancelReminder,
    CreateReminder,
    DeviceConnected,
    DeviceMessage,
    PresenceChanged,
    UserText,
)

DEVICE_MESSAGE_MODELS = {
    "DEVICE_CONNECTED": DeviceConnected,
    "USER_TEXT": UserText,
    "BUTTON_PRESSED": ButtonPressed,
    "PRESENCE_CHANGED": PresenceChanged,
    "CREATE_REMINDER": CreateReminder,
    "CANCEL_REMINDER": CancelReminder,
}


class ProtocolMessageError(ValueError):
    """Raised when an incoming payload is not a valid protocol message."""


def parse_device_message(payload: str) -> DeviceMessage:
    """Parse JSON into the explicitly selected Pydantic message model."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ProtocolMessageError("message is not valid JSON") from exc

    if not isinstance(data, Mapping):
        raise ProtocolMessageError("message must be a JSON object")

    message_type = data.get("type")
    model = DEVICE_MESSAGE_MODELS.get(message_type)
    if model is None:
        raise ProtocolMessageError(f"unknown message type: {message_type!r}")

    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise ProtocolMessageError(f"invalid {message_type} payload") from exc
