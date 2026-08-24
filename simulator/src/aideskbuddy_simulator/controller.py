"""Coordinate Desk Buddy behavior without desktop UI dependencies."""

import math

from aideskbuddy_simulator.core.state import DeskBuddyState, StateMachine
from aideskbuddy_simulator.face.controller import (
    Expression,
    FaceController,
    LookDirection,
)
from aideskbuddy_simulator.features.notification import Notification
from aideskbuddy_simulator.features.timer import Timer, TimerStatus

EXPRESSION_FOR_STATE = {
    DeskBuddyState.IDLE: Expression.NORMAL,
    DeskBuddyState.LISTENING: Expression.LISTENING,
    DeskBuddyState.THINKING: Expression.THINKING,
    DeskBuddyState.SPEAKING: Expression.SPEAKING,
    DeskBuddyState.TIMER: Expression.TIMER,
    DeskBuddyState.NOTIFICATION: Expression.SURPRISED,
    DeskBuddyState.SLEEPING: Expression.SLEEPING,
    DeskBuddyState.ERROR: Expression.ERROR,
}


class SimulatorController:
    """Translate simulator actions into state, face, and timer behavior."""

    def __init__(
        self,
        *,
        initial_state: DeskBuddyState = DeskBuddyState.IDLE,
        timer_duration_seconds: float = 60.0,
        notification_duration_seconds: float = 2.5,
    ) -> None:
        self.state_machine = StateMachine(initial_state)
        self.face = FaceController()
        self.timer = Timer(timer_duration_seconds)
        self.notification = Notification(notification_duration_seconds)
        self.buddy_text: str | None = None
        self._buddy_text_remaining = 0.0
        self._speaking_return_state: DeskBuddyState | None = None
        self.face.set_expression(EXPRESSION_FOR_STATE[initial_state])

    @property
    def state(self) -> DeskBuddyState:
        return self.state_machine.state

    @property
    def timer_text(self) -> str:
        total_seconds = math.ceil(self.timer.remaining_seconds)
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def timer_status_text(self) -> str | None:
        return "PAUSED" if self.timer.status is TimerStatus.PAUSED else None

    @property
    def notification_text(self) -> str | None:
        return self.notification.text

    def set_face_expression(self, expression: Expression) -> None:
        """Set a face expression from a simulator/debug adapter."""
        self.face.set_expression(expression)

    def look_at(self, direction: LookDirection) -> None:
        """Move the face gaze from a simulator/debug adapter."""
        self.face.look_at(direction)

    def blink(self) -> None:
        self.face.blink()

    def handle_server_message(self, message: dict[str, object]) -> None:
        """Apply a validated-by-server command to the simulated display."""
        message_type = message.get("type")
        if message_type == "STATE_CHANGED":
            state_name = message.get("state")
            state_map = {
                "ALERT": DeskBuddyState.NOTIFICATION,
                "OFFLINE": DeskBuddyState.ERROR,
            }
            try:
                state = state_map.get(str(state_name))
                if state is None:
                    state = DeskBuddyState(str(state_name))
            except ValueError:
                return
            self._speaking_return_state = None
            self._apply_state(state)
        elif message_type == "DISPLAY_TEXT" and isinstance(message.get("text"), str):
            self._show_buddy_text(str(message["text"]))
        elif message_type == "SPEAK" and isinstance(message.get("text"), str):
            self._show_buddy_text(str(message["text"]))
            if self.state is not DeskBuddyState.SPEAKING:
                self._speaking_return_state = self.state
            self._apply_state(DeskBuddyState.SPEAKING)

    def select_state(self, state: DeskBuddyState) -> None:
        """Manually select a state for expression testing."""
        if state is not DeskBuddyState.TIMER and self.timer.is_active:
            self.timer.cancel()
        self.notification.dismiss()
        self._apply_state(state)

    def adjust_timer(self, seconds: float) -> bool:
        """Adjust inactive timer duration, clamped to at least one second."""
        if self.timer.is_active:
            return False
        duration = max(1.0, self.timer.duration_seconds + seconds)
        self.timer.set_duration(duration)
        self._apply_state(DeskBuddyState.TIMER)
        return True

    def start_timer(self) -> bool:
        if not self.timer.start():
            return False
        self.notification.dismiss()
        self._apply_state(DeskBuddyState.TIMER)
        return True

    def pause_timer(self) -> bool:
        return self.timer.pause()

    def resume_timer(self) -> bool:
        return self.timer.resume()

    def cancel_timer(self) -> bool:
        was_active = self.timer.cancel()
        self.notification.dismiss()
        self._apply_state(DeskBuddyState.IDLE)
        return was_active

    def show_notification(
        self,
        text: str,
        *,
        duration_seconds: float | None = None,
        return_state: DeskBuddyState | None = None,
    ) -> None:
        """Show a temporary message and remember which state to restore."""
        previous_state = return_state
        if previous_state is None:
            if self.notification.is_active:
                previous_state = self.notification.return_state
            elif self.state is DeskBuddyState.NOTIFICATION:
                previous_state = DeskBuddyState.IDLE
            else:
                previous_state = self.state
        self.notification.show(
            text,
            previous_state or DeskBuddyState.IDLE,
            duration_seconds=duration_seconds,
        )
        self._apply_state(DeskBuddyState.NOTIFICATION)

    def update(self, delta_seconds: float) -> None:
        self.face.update(delta_seconds)
        if self.timer.update(delta_seconds):
            self._show_timer_completion()
            return

        restore_state = self.notification.update(delta_seconds)
        if restore_state is not None:
            self._apply_state(restore_state)

        if self._buddy_text_remaining > 0:
            self._buddy_text_remaining -= delta_seconds
            if self._buddy_text_remaining <= 1e-9:
                self.buddy_text = None
                self._buddy_text_remaining = 0.0
                if self._speaking_return_state is not None:
                    return_state = self._speaking_return_state
                    self._speaking_return_state = None
                    self._apply_state(return_state)

    def _show_timer_completion(self) -> None:
        self.show_notification(
            "Timer complete!",
            return_state=DeskBuddyState.IDLE,
        )

    def _apply_state(self, state: DeskBuddyState) -> None:
        self.state_machine.transition_to(state)
        self.face.set_expression(EXPRESSION_FOR_STATE[state])

    def _show_buddy_text(self, text: str) -> None:
        self.buddy_text = text
        self._buddy_text_remaining = 3.0
