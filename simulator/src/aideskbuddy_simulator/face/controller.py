"""Frame-rate-independent face animation controller."""

import math
import random
from collections.abc import Callable
from enum import StrEnum

from aideskbuddy_simulator.config import BlinkConfig
from aideskbuddy_simulator.face.animation import AnimatedValue
from aideskbuddy_simulator.face.pose import FacePose, MouthShape


class Expression(StrEnum):
    """Renderer-independent expressions supported by the face."""

    NORMAL = "NORMAL"
    HAPPY = "HAPPY"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    TIMER = "TIMER"
    SURPRISED = "SURPRISED"
    SLEEPING = "SLEEPING"
    ERROR = "ERROR"


class LookDirection(StrEnum):
    """Named gaze targets exposed by the reusable face API."""

    CENTER = "CENTER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UP = "UP"
    DOWN = "DOWN"


GAZE_TARGETS = {
    LookDirection.CENTER: (0.0, 0.0),
    LookDirection.LEFT: (-14.0, 0.0),
    LookDirection.RIGHT: (14.0, 0.0),
    LookDirection.UP: (0.0, -11.0),
    LookDirection.DOWN: (0.0, 11.0),
}


class FaceController:
    """Manage face animation without depending on desktop UI objects."""

    def __init__(
        self,
        config: BlinkConfig | None = None,
        *,
        random_uniform: Callable[[float, float], float] | None = None,
    ) -> None:
        self._config = config or BlinkConfig()
        self._random_uniform = random_uniform or random.uniform
        self._blink_elapsed: float | None = None
        self._time_until_blink = self._next_blink_interval()
        self._expression = Expression.NORMAL
        self._animation_elapsed = 0.0
        self._look_direction = LookDirection.CENTER
        self._gaze_x = AnimatedValue()
        self._gaze_y = AnimatedValue()

    @property
    def expression(self) -> Expression:
        return self._expression

    @property
    def animation_elapsed(self) -> float:
        return self._animation_elapsed

    @property
    def look_direction(self) -> LookDirection:
        return self._look_direction

    @property
    def pose(self) -> FacePose:
        """Return coordinated eye and mouth geometry for the current frame."""
        speaking_phase = (math.sin(self._animation_elapsed * 10.0) + 1.0) / 2.0
        poses = {
            Expression.NORMAL: FacePose(mouth_shape=MouthShape.NEUTRAL),
            Expression.HAPPY: FacePose(
                eye_width_scale=1.04,
                eye_tilt_degrees=9.0,
                mouth_shape=MouthShape.SMILE,
                mouth_width_scale=1.2,
            ),
            Expression.LISTENING: FacePose(
                eye_width_scale=1.05,
                eye_height_scale=1.08,
                mouth_shape=MouthShape.NEUTRAL,
            ),
            Expression.THINKING: FacePose(
                eye_height_scale=0.94,
                eye_tilt_degrees=-3.0,
                mouth_shape=MouthShape.THINKING,
            ),
            Expression.SPEAKING: FacePose(
                eye_height_scale=0.96,
                mouth_shape=MouthShape.OPEN,
                mouth_openness=0.3 + 0.7 * speaking_phase,
                face_y_offset=1.5 * math.sin(self._animation_elapsed * 8.0),
            ),
            Expression.TIMER: FacePose(
                mouth_shape=MouthShape.NEUTRAL,
            ),
            Expression.SURPRISED: FacePose(
                eye_width_scale=1.12,
                eye_height_scale=1.1,
                mouth_shape=MouthShape.SURPRISED,
                mouth_openness=1.0,
            ),
            Expression.SLEEPING: FacePose(
                mouth_shape=MouthShape.SLEEPING,
                mouth_width_scale=0.85,
            ),
            Expression.ERROR: FacePose(
                eye_width_scale=1.02,
                eye_tilt_degrees=-11.0,
                mouth_shape=MouthShape.ERROR,
            ),
        }
        return poses[self._expression]

    @property
    def is_blinking(self) -> bool:
        return self._blink_elapsed is not None

    @property
    def eye_openness(self) -> float:
        """Return eye openness between fully closed (0) and open (1)."""
        base_openness = {
            Expression.NORMAL: 0.9,
            Expression.HAPPY: 0.62,
            Expression.LISTENING: 1.0,
            Expression.THINKING: 0.82,
            Expression.SPEAKING: 0.76
            + 0.12 * math.sin(self._animation_elapsed * 9.0),
            Expression.TIMER: 0.9,
            Expression.SURPRISED: 1.0,
            Expression.SLEEPING: 0.0,
            Expression.ERROR: 0.56,
        }[self._expression]

        if self._blink_elapsed is None:
            return base_openness

        elapsed = self._blink_elapsed
        close_end = self._config.close_duration
        closed_end = close_end + self._config.closed_duration

        if elapsed < close_end:
            blink_openness = max(0.0, 1.0 - elapsed / close_end)
            return base_openness * blink_openness
        if elapsed < closed_end:
            return 0.0

        opening_elapsed = elapsed - closed_end
        blink_openness = min(1.0, opening_elapsed / self._config.open_duration)
        return base_openness * blink_openness

    @property
    def eye_scale(self) -> float:
        return self.pose.eye_width_scale

    @property
    def gaze_offset(self) -> tuple[float, float]:
        """Return the animated pupil offset in virtual-display pixels."""
        if self._expression is Expression.THINKING:
            return (
                13.0 * math.sin(self._animation_elapsed * 2.1),
                5.0 * math.sin(self._animation_elapsed * 1.3),
            )
        subtle_idle_x = 0.0
        if (
            self._expression is Expression.NORMAL
            and self._look_direction is LookDirection.CENTER
        ):
            subtle_idle_x = 1.5 * math.sin(self._animation_elapsed * 0.7)
        return (self._gaze_x.value + subtle_idle_x, self._gaze_y.value)

    def set_expression(self, expression: Expression) -> None:
        """Set the expression used by subsequent animation updates."""
        expression_changed = expression is not self._expression
        self._expression = expression
        if expression_changed:
            self._animation_elapsed = 0.0
        self.look_at(LookDirection.CENTER)
        if expression in {Expression.SLEEPING, Expression.ERROR}:
            self._blink_elapsed = None

    def look_at(self, direction: LookDirection) -> None:
        """Smoothly move the eyes toward a named gaze direction."""
        self._look_direction = direction
        target_x, target_y = GAZE_TARGETS[direction]
        self._gaze_x.set_target(target_x)
        self._gaze_y.set_target(target_y)

    def blink(self) -> None:
        """Start a blink unless one is already in progress."""
        if not self.is_blinking:
            self._blink_elapsed = 0.0

    def update(self, delta_seconds: float) -> None:
        """Advance animations by elapsed wall-clock time."""
        if delta_seconds < 0:
            raise ValueError("delta_seconds must not be negative")

        self._animation_elapsed += delta_seconds
        self._gaze_x.update(delta_seconds)
        self._gaze_y.update(delta_seconds)

        if self._expression not in {
            Expression.NORMAL,
            Expression.HAPPY,
            Expression.LISTENING,
            Expression.TIMER,
        }:
            return

        if self._blink_elapsed is None:
            self._time_until_blink -= delta_seconds
            if self._time_until_blink <= 0:
                self.blink()
            return

        self._blink_elapsed += delta_seconds
        if self._blink_elapsed >= self._config.total_duration:
            self._blink_elapsed = None
            self._time_until_blink = self._next_blink_interval()

    def _next_blink_interval(self) -> float:
        return self._random_uniform(
            self._config.interval_min,
            self._config.interval_max,
        )
