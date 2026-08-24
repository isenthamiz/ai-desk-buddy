"""Small frame-rate-independent animation primitives."""

import math


class AnimatedValue:
    """Smoothly approach a target value without blocking the update loop."""

    def __init__(self, initial: float = 0.0, response: float = 12.0) -> None:
        if response <= 0:
            raise ValueError("response must be greater than zero")
        self._value = initial
        self._target = initial
        self._response = response

    @property
    def value(self) -> float:
        return self._value

    @property
    def target(self) -> float:
        return self._target

    def set_target(self, target: float) -> None:
        self._target = target

    def update(self, delta_seconds: float) -> None:
        if delta_seconds < 0:
            raise ValueError("delta_seconds must not be negative")
        blend = 1.0 - math.exp(-self._response * delta_seconds)
        self._value += (self._target - self._value) * blend
