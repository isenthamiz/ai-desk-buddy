"""Unit tests for backend-owned timer lifecycle."""

import asyncio

import pytest

from aideskbuddy.timer import TimerService


@pytest.mark.asyncio
async def test_timer_completes_once() -> None:
    completions = 0

    async def complete() -> None:
        nonlocal completions
        completions += 1

    timer = TimerService(complete)
    assert timer.start(0.01)  # type: ignore[arg-type]
    assert not timer.start(1)
    await asyncio.sleep(0.02)

    assert completions == 1
    assert not timer.is_active


@pytest.mark.asyncio
async def test_timer_can_be_cancelled_and_closed() -> None:
    completed = asyncio.Event()

    async def complete() -> None:
        completed.set()

    timer = TimerService(complete)
    assert timer.start(60)
    assert timer.cancel()
    assert not timer.cancel()
    await timer.close()
    assert not completed.is_set()
