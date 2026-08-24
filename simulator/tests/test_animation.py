"""Tests for reusable animation primitives."""

import pytest

from aideskbuddy_simulator.face.animation import AnimatedValue


def test_animated_value_smoothly_approaches_target() -> None:
    value = AnimatedValue(response=10)
    value.set_target(20)

    value.update(0.05)
    first_value = value.value
    value.update(0.05)

    assert 0 < first_value < value.value < 20


def test_animated_value_rejects_negative_time() -> None:
    value = AnimatedValue()

    with pytest.raises(ValueError, match="must not be negative"):
        value.update(-0.1)
