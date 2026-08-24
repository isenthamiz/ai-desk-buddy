"""Authoritative, in-memory timer lifecycle for one device connection."""

import asyncio
from collections.abc import Awaitable, Callable

TimerCompletionHandler = Callable[[], Awaitable[None]]


class TimerService:
    """Manage a single cancellable timer for one connected device."""

    def __init__(self, on_complete: TimerCompletionHandler) -> None:
        self._on_complete = on_complete
        self._task: asyncio.Task[None] | None = None
        self._duration_seconds: int | None = None

    @property
    def is_active(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def duration_seconds(self) -> int | None:
        return self._duration_seconds if self.is_active else None

    def start(self, duration_seconds: int) -> bool:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than zero")
        if self.is_active:
            return False
        self._duration_seconds = duration_seconds
        self._task = asyncio.create_task(self._run(duration_seconds))
        return True

    def cancel(self) -> bool:
        if not self.is_active:
            return False
        assert self._task is not None
        self._task.cancel()
        self._task = None
        self._duration_seconds = None
        return True

    async def close(self) -> None:
        task = self._task
        self._task = None
        self._duration_seconds = None
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _run(self, duration_seconds: int) -> None:
        try:
            await asyncio.sleep(duration_seconds)
            self._task = None
            self._duration_seconds = None
            await self._on_complete()
        except asyncio.CancelledError:
            raise
