"""UI-independent Desk Buddy state model."""

from enum import StrEnum
import logging

LOGGER = logging.getLogger(__name__)


class DeskBuddyState(StrEnum):
    """Desk Buddy experience states supported by the simulator."""

    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    TIMER = "TIMER"
    NOTIFICATION = "NOTIFICATION"
    SLEEPING = "SLEEPING"
    ERROR = "ERROR"


class StateMachine:
    """Own the current Desk Buddy state independently of the renderer."""

    def __init__(self, initial_state: DeskBuddyState = DeskBuddyState.IDLE) -> None:
        self._state = initial_state
        LOGGER.info("Desk Buddy initial state: %s", initial_state.value)

    @property
    def state(self) -> DeskBuddyState:
        return self._state

    def transition_to(self, state: DeskBuddyState) -> bool:
        """Transition to ``state`` and report whether the state changed."""
        if state is self._state:
            return False

        previous = self._state
        self._state = state
        LOGGER.info(
            "Desk Buddy state transition: %s -> %s",
            previous.value,
            state.value,
        )
        return True
