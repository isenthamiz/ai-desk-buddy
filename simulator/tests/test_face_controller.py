"""Tests for UI-independent face animation behavior."""

import pytest

from aideskbuddy_simulator.config import BlinkConfig
from aideskbuddy_simulator.face.controller import (
    Expression,
    FaceController,
    LookDirection,
)


@pytest.fixture
def blink_config() -> BlinkConfig:
    return BlinkConfig(
        interval_min=1.0,
        interval_max=1.0,
        close_duration=0.1,
        closed_duration=0.05,
        open_duration=0.1,
    )


def test_idle_face_blinks_and_returns_to_open(blink_config: BlinkConfig) -> None:
    face = FaceController(blink_config, random_uniform=lambda _a, _b: 1.0)

    face.update(1.0)
    assert face.is_blinking

    face.update(0.1)
    assert face.eye_openness == pytest.approx(0.0)

    face.update(0.05)
    assert face.eye_openness == pytest.approx(0.0)

    face.update(0.05)
    assert face.eye_openness == pytest.approx(0.45)

    face.update(0.05)
    assert not face.is_blinking
    assert face.eye_openness == pytest.approx(0.9)


def test_manual_blink_does_not_restart_mid_animation(
    blink_config: BlinkConfig,
) -> None:
    face = FaceController(blink_config)
    face.blink()
    face.update(0.05)
    openness_before_second_blink = face.eye_openness

    face.blink()

    assert face.eye_openness == openness_before_second_blink


def test_negative_update_is_rejected(blink_config: BlinkConfig) -> None:
    face = FaceController(blink_config)

    with pytest.raises(ValueError, match="must not be negative"):
        face.update(-0.01)


@pytest.mark.parametrize("expression", list(Expression))
def test_every_expression_produces_a_valid_pose(expression: Expression) -> None:
    face = FaceController()
    face.set_expression(expression)
    face.update(0.1)

    assert 0.0 <= face.eye_openness <= 1.0
    assert len(face.gaze_offset) == 2


def test_sleeping_expression_closes_eyes() -> None:
    face = FaceController()

    face.set_expression(Expression.SLEEPING)

    assert face.eye_openness == 0.0


@pytest.mark.parametrize(
    ("direction", "expected_axis", "expected_sign"),
    [
        (LookDirection.LEFT, 0, -1),
        (LookDirection.RIGHT, 0, 1),
        (LookDirection.UP, 1, -1),
        (LookDirection.DOWN, 1, 1),
    ],
)
def test_look_at_smoothly_moves_toward_each_direction(
    direction: LookDirection,
    expected_axis: int,
    expected_sign: int,
) -> None:
    face = FaceController()
    face.look_at(direction)

    assert face.gaze_offset[expected_axis] == pytest.approx(0.0)
    face.update(0.05)
    first_offset = face.gaze_offset[expected_axis]
    face.update(0.05)
    second_offset = face.gaze_offset[expected_axis]

    assert first_offset * expected_sign > 0
    assert abs(second_offset) > abs(first_offset)


def test_happy_expression_has_smiling_eye_shape() -> None:
    face = FaceController()

    face.set_expression(Expression.HAPPY)

    assert face.eye_openness == pytest.approx(0.62)
