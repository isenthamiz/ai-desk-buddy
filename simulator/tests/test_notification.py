"""Tests for temporary notification lifecycle behavior."""

import pytest

from aideskbuddy_simulator.core.state import DeskBuddyState
from aideskbuddy_simulator.features.notification import Notification


def test_notification_expires_to_saved_state() -> None:
    notification = Notification(default_duration_seconds=2)
    notification.show("Meeting in 10 minutes", DeskBuddyState.THINKING)

    assert notification.is_active
    assert notification.text == "Meeting in 10 minutes"
    assert notification.update(1.9) is None
    assert notification.update(0.1) is DeskBuddyState.THINKING
    assert not notification.is_active


def test_notification_can_override_duration() -> None:
    notification = Notification(default_duration_seconds=10)
    notification.show(
        "Short message",
        DeskBuddyState.IDLE,
        duration_seconds=1,
    )

    assert notification.update(1) is DeskBuddyState.IDLE


@pytest.mark.parametrize("text", ["", "   "])
def test_notification_rejects_empty_text(text: str) -> None:
    notification = Notification()

    with pytest.raises(ValueError, match="must not be empty"):
        notification.show(text, DeskBuddyState.IDLE)


def test_notification_rejects_invalid_duration() -> None:
    notification = Notification()

    with pytest.raises(ValueError, match="greater than zero"):
        notification.show("Hello", DeskBuddyState.IDLE, duration_seconds=0)
