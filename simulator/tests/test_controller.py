"""Tests for timer-driven Desk Buddy behavior."""

from aideskbuddy_simulator.controller import SimulatorController
from aideskbuddy_simulator.core.state import DeskBuddyState
from aideskbuddy_simulator.features.timer import TimerStatus


def test_start_pause_resume_and_cancel_timer() -> None:
    controller = SimulatorController(timer_duration_seconds=10)

    assert controller.start_timer()
    assert controller.state is DeskBuddyState.TIMER
    controller.update(2)
    assert controller.timer_text == "00:08"

    assert controller.pause_timer()
    controller.update(3)
    assert controller.timer_text == "00:08"
    assert controller.timer_status_text == "PAUSED"

    assert controller.resume_timer()
    assert controller.timer.status is TimerStatus.RUNNING
    assert controller.cancel_timer()
    assert controller.state is DeskBuddyState.IDLE
    assert controller.timer_text == "00:10"


def test_timer_completion_notifies_then_returns_to_idle() -> None:
    controller = SimulatorController(
        timer_duration_seconds=1,
        notification_duration_seconds=2,
    )
    controller.start_timer()

    controller.update(1)
    assert controller.state is DeskBuddyState.NOTIFICATION
    assert controller.notification_text == "Timer complete!"

    controller.update(1.9)
    assert controller.state is DeskBuddyState.NOTIFICATION
    controller.update(0.1)
    assert controller.state is DeskBuddyState.IDLE
    assert controller.notification_text is None


def test_inactive_duration_can_be_adjusted_but_active_duration_cannot() -> None:
    controller = SimulatorController(timer_duration_seconds=10)

    assert controller.adjust_timer(10)
    assert controller.timer_text == "00:20"
    assert controller.state is DeskBuddyState.TIMER
    controller.start_timer()
    assert not controller.adjust_timer(10)
    assert controller.timer.duration_seconds == 20


def test_notification_restores_previous_state() -> None:
    controller = SimulatorController(
        initial_state=DeskBuddyState.THINKING,
        notification_duration_seconds=2,
    )

    controller.show_notification("Meeting in 10 minutes")
    assert controller.state is DeskBuddyState.NOTIFICATION
    assert controller.notification_text == "Meeting in 10 minutes"

    controller.update(2)
    assert controller.state is DeskBuddyState.THINKING
    assert controller.notification_text is None


def test_notification_during_timer_restores_active_timer() -> None:
    controller = SimulatorController(
        timer_duration_seconds=10,
        notification_duration_seconds=2,
    )
    controller.start_timer()
    controller.update(1)

    controller.show_notification("Meeting soon")
    controller.update(2)

    assert controller.state is DeskBuddyState.TIMER
    assert controller.timer.status is TimerStatus.RUNNING
    assert controller.timer_text == "00:07"


def test_server_state_command_changes_face_state() -> None:
    controller = SimulatorController()

    controller.handle_server_message(
        {"type": "STATE_CHANGED", "state": "LISTENING"}
    )

    assert controller.state is DeskBuddyState.LISTENING


def test_server_speak_command_temporarily_drives_speaking_reaction() -> None:
    controller = SimulatorController(initial_state=DeskBuddyState.IDLE)

    controller.handle_server_message({"type": "SPEAK", "text": "Hello!"})
    assert controller.state is DeskBuddyState.SPEAKING
    assert controller.buddy_text == "Hello!"

    controller.update(3)
    assert controller.state is DeskBuddyState.IDLE
    assert controller.buddy_text is None
