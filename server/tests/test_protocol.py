"""Protocol v0.1 validation tests."""

import pytest

from aideskbuddy.protocol import (
    ButtonPressed,
    DeviceConnected,
    PresenceChanged,
    ProtocolMessageError,
    UserText,
    TimerStarted,
    parse_device_message,
)


@pytest.mark.parametrize(
    ("payload", "model"),
    [
        (
            '{"type":"DEVICE_CONNECTED","deviceId":"sim-1",'
            '"deviceType":"SIMULATOR"}',
            DeviceConnected,
        ),
        ('{"type":"USER_TEXT","text":"Hello"}', UserText),
        ('{"type":"BUTTON_PRESSED","button":"ACTION"}', ButtonPressed),
        ('{"type":"PRESENCE_CHANGED","present":true}', PresenceChanged),
    ],
)
def test_parse_valid_device_messages(payload: str, model: type) -> None:
    assert isinstance(parse_device_message(payload), model)


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        "[]",
        '{"type":"UNKNOWN"}',
        '{"type":"USER_TEXT","text":""}',
        '{"type":"PRESENCE_CHANGED","present":"yes"}',
    ],
)
def test_invalid_messages_fail_safely(payload: str) -> None:
    with pytest.raises(ProtocolMessageError):
        parse_device_message(payload)


def test_request_id_and_additive_fields_are_supported() -> None:
    message = parse_device_message(
        '{"type":"USER_TEXT","text":"Hello","requestId":"abc",'
        '"futureField":true}'
    )

    assert message.request_id == "abc"


def test_timer_started_serializes_camel_case_duration() -> None:
    message = TimerStarted(durationSeconds=90)

    assert message.model_dump(mode="json", by_alias=True, exclude_none=True) == {
        "type": "TIMER_STARTED",
        "durationSeconds": 90,
    }
