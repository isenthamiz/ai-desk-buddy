"""UI-independent countdown timer."""

from enum import StrEnum


class TimerStatus(StrEnum):
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class Timer:
    """A deterministic countdown advanced by the application's update loop."""

    def __init__(self, duration_seconds: float = 60.0) -> None:
        self._validate_duration(duration_seconds)
        self._duration_seconds = duration_seconds
        self._remaining_seconds = duration_seconds
        self._status = TimerStatus.READY

    @property
    def duration_seconds(self) -> float:
        return self._duration_seconds

    @property
    def remaining_seconds(self) -> float:
        return self._remaining_seconds

    @property
    def status(self) -> TimerStatus:
        return self._status

    @property
    def is_active(self) -> bool:
        return self._status in {TimerStatus.RUNNING, TimerStatus.PAUSED}

    def set_duration(self, duration_seconds: float) -> None:
        """Set a new duration while the timer is inactive."""
        self._validate_duration(duration_seconds)
        if self.is_active:
            raise RuntimeError("cannot change an active timer")
        self._duration_seconds = duration_seconds
        self._remaining_seconds = duration_seconds
        self._status = TimerStatus.READY

    def start(self) -> bool:
        """Start a fresh countdown."""
        if self.is_active:
            return False
        self._remaining_seconds = self._duration_seconds
        self._status = TimerStatus.RUNNING
        return True

    def pause(self) -> bool:
        if self._status is not TimerStatus.RUNNING:
            return False
        self._status = TimerStatus.PAUSED
        return True

    def resume(self) -> bool:
        if self._status is not TimerStatus.PAUSED:
            return False
        self._status = TimerStatus.RUNNING
        return True

    def cancel(self) -> bool:
        was_active = self.is_active
        self._remaining_seconds = self._duration_seconds
        self._status = TimerStatus.READY
        return was_active

    def update(self, delta_seconds: float) -> bool:
        """Advance the timer and return true exactly when it completes."""
        if delta_seconds < 0:
            raise ValueError("delta_seconds must not be negative")
        if self._status is not TimerStatus.RUNNING:
            return False

        self._remaining_seconds = max(0.0, self._remaining_seconds - delta_seconds)
        if self._remaining_seconds > 0:
            return False

        self._status = TimerStatus.COMPLETED
        return True

    @staticmethod
    def _validate_duration(duration_seconds: float) -> None:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than zero")
