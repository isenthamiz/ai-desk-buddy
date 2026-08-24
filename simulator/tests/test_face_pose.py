"""Tests for coordinated eye and mouth poses."""

import pytest

from aideskbuddy_simulator.face.controller import Expression, FaceController
from aideskbuddy_simulator.face.pose import MouthShape


@pytest.mark.parametrize(
    ("expression", "mouth_shape"),
    [
        (Expression.NORMAL, MouthShape.NEUTRAL),
        (Expression.HAPPY, MouthShape.SMILE),
        (Expression.LISTENING, MouthShape.NEUTRAL),
        (Expression.THINKING, MouthShape.THINKING),
        (Expression.SPEAKING, MouthShape.OPEN),
        (Expression.TIMER, MouthShape.NEUTRAL),
        (Expression.SURPRISED, MouthShape.SURPRISED),
        (Expression.SLEEPING, MouthShape.SLEEPING),
        (Expression.ERROR, MouthShape.ERROR),
    ],
)
def test_expression_maps_to_coordinated_mouth_shape(
    expression: Expression,
    mouth_shape: MouthShape,
) -> None:
    face = FaceController()

    face.set_expression(expression)

    assert face.pose.mouth_shape is mouth_shape
    assert face.pose.eye_width_scale > 0
    assert face.pose.eye_height_scale > 0


def test_speaking_animates_mouth_without_blocking() -> None:
    face = FaceController()
    face.set_expression(Expression.SPEAKING)
    initial_openness = face.pose.mouth_openness

    face.update(0.1)

    assert face.pose.mouth_openness != pytest.approx(initial_openness)
    assert 0 <= face.pose.mouth_openness <= 1
