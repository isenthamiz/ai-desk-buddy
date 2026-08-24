"""Tests for the UI-independent timer model."""

import pytest

from aideskbuddy_simulator.features.timer import Timer, TimerStatus


def test_timer_counts_down_and_completes_once() -> None:
    timer = Timer(5)

    assert timer.start()
    assert not timer.update(3)
    assert timer.remaining_seconds == pytest.approx(2)
    assert timer.update(2)
    assert timer.status is TimerStatus.COMPLETED
    assert timer.remaining_seconds == 0
    assert not timer.update(1)


def test_timer_can_pause_and_resume() -> None:
    timer = Timer(5)
    timer.start()
    timer.update(1)

    assert timer.pause()
    timer.update(2)
    assert timer.remaining_seconds == pytest.approx(4)
    assert timer.resume()
    timer.update(1)
    assert timer.remaining_seconds == pytest.approx(3)


def test_cancel_resets_timer() -> None:
    timer = Timer(5)
    timer.start()
    timer.update(2)

    assert timer.cancel()
    assert timer.status is TimerStatus.READY
    assert timer.remaining_seconds == 5


def test_duration_can_only_change_while_inactive() -> None:
    timer = Timer(5)
    timer.set_duration(10)
    assert timer.duration_seconds == 10

    timer.start()
    with pytest.raises(RuntimeError, match="active timer"):
        timer.set_duration(20)


@pytest.mark.parametrize("duration", [0, -1])
def test_duration_must_be_positive(duration: float) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        Timer(duration)
