"""Tests for Desk Buddy state transitions."""

import logging

from aideskbuddy_simulator.core.state import DeskBuddyState, StateMachine


def test_all_required_states_are_available() -> None:
    assert set(DeskBuddyState) == {
        DeskBuddyState.IDLE,
        DeskBuddyState.LISTENING,
        DeskBuddyState.THINKING,
        DeskBuddyState.SPEAKING,
        DeskBuddyState.TIMER,
        DeskBuddyState.NOTIFICATION,
        DeskBuddyState.SLEEPING,
        DeskBuddyState.ERROR,
    }


def test_transition_changes_state_and_is_logged(caplog) -> None:
    machine = StateMachine()

    with caplog.at_level(logging.INFO):
        changed = machine.transition_to(DeskBuddyState.THINKING)

    assert changed
    assert machine.state is DeskBuddyState.THINKING
    assert "IDLE -> THINKING" in caplog.text
