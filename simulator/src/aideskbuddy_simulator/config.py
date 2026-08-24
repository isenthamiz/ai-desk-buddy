"""Display and animation configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DisplayConfig:
    """Dimensions for the virtual device display and desktop window."""

    virtual_width: int = 240
    virtual_height: int = 240
    window_scale: int = 2
    frames_per_second: int = 60

    @property
    def window_size(self) -> tuple[int, int]:
        return (
            self.virtual_width * self.window_scale,
            self.virtual_height * self.window_scale,
        )


@dataclass(frozen=True, slots=True)
class BlinkConfig:
    """Timing for calm, natural idle blinking, in seconds."""

    interval_min: float = 2.5
    interval_max: float = 5.5
    close_duration: float = 0.09
    closed_duration: float = 0.04
    open_duration: float = 0.13

    @property
    def total_duration(self) -> float:
        return self.close_duration + self.closed_duration + self.open_duration
