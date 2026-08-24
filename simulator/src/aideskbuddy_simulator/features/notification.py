"""UI-independent temporary notification lifecycle."""

from aideskbuddy_simulator.core.state import DeskBuddyState


class Notification:
    """Track an active message and the state to restore afterward."""

    def __init__(self, default_duration_seconds: float = 2.5) -> None:
        self._validate_duration(default_duration_seconds)
        self._default_duration_seconds = default_duration_seconds
        self._remaining_seconds = 0.0
        self._text: str | None = None
        self._return_state: DeskBuddyState | None = None

    @property
    def is_active(self) -> bool:
        return self._text is not None

    @property
    def text(self) -> str | None:
        return self._text

    @property
    def return_state(self) -> DeskBuddyState | None:
        return self._return_state

    def show(
        self,
        text: str,
        return_state: DeskBuddyState,
        *,
        duration_seconds: float | None = None,
    ) -> None:
        message = text.strip()
        if not message:
            raise ValueError("notification text must not be empty")
        duration = (
            self._default_duration_seconds
            if duration_seconds is None
            else duration_seconds
        )
        self._validate_duration(duration)
        self._text = message
        self._return_state = return_state
        self._remaining_seconds = duration

    def update(self, delta_seconds: float) -> DeskBuddyState | None:
        """Advance the notification and return its restore state on expiry."""
        if delta_seconds < 0:
            raise ValueError("delta_seconds must not be negative")
        if not self.is_active:
            return None

        self._remaining_seconds -= delta_seconds
        if self._remaining_seconds > 1e-9:
            return None
        return self.dismiss()

    def dismiss(self) -> DeskBuddyState | None:
        return_state = self._return_state
        self._text = None
        self._return_state = None
        self._remaining_seconds = 0.0
        return return_state

    @staticmethod
    def _validate_duration(duration_seconds: float) -> None:
        if duration_seconds <= 0:
            raise ValueError("notification duration must be greater than zero")
