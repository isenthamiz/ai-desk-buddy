"""Reminder lifecycle and durable delivery scheduling."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from aideskbuddy.reminder.model import Reminder, ReminderStatus
from aideskbuddy.reminder.repository import SQLiteReminderRepository

Clock = Callable[[], datetime]
ReminderNotifier = Callable[[Reminder], Awaitable[bool]]
LOGGER = logging.getLogger(__name__)


class ReminderService:
    def __init__(
        self,
        repository: SQLiteReminderRepository,
        notifier: ReminderNotifier,
        *,
        clock: Clock | None = None,
        poll_interval: float = 1.0,
    ) -> None:
        self._repository = repository
        self._notifier = notifier
        self._clock = clock or (lambda: datetime.now(UTC))
        self._poll_interval = poll_interval
        self._wake = asyncio.Event()
        self._delivery_lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def close(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    def create(self, device_id: str, text: str, due_at: datetime) -> Reminder:
        if due_at.tzinfo is None or due_at.utcoffset() is None:
            raise ValueError("due_at must include a UTC offset")
        now = self._clock().astimezone(UTC)
        reminder = Reminder(
            id=str(uuid4()),
            device_id=device_id,
            text=text.strip(),
            due_at=due_at.astimezone(UTC),
            status=ReminderStatus.PENDING,
            created_at=now,
        )
        if not reminder.text:
            raise ValueError("reminder text must not be empty")
        self._repository.add(reminder)
        self._wake.set()
        return reminder

    def create_in(self, device_id: str, text: str, delay_seconds: int) -> Reminder:
        """Create a reminder relative to the authoritative backend clock."""
        if delay_seconds <= 0:
            raise ValueError("delay_seconds must be greater than zero")
        due_at = self._clock().astimezone(UTC) + timedelta(seconds=delay_seconds)
        return self.create(device_id, text, due_at)

    def cancel(self, device_id: str, reminder_id: str) -> bool:
        return self._repository.cancel(reminder_id, device_id)

    async def deliver_due(self, device_id: str | None = None) -> None:
        async with self._delivery_lock:
            now = self._clock().astimezone(UTC)
            for reminder in self._repository.due(now, device_id=device_id):
                try:
                    sent = await self._notifier(reminder)
                except Exception:
                    LOGGER.exception("Could not deliver reminder %s", reminder.id)
                    sent = False
                if sent:
                    self._repository.mark_delivered(
                        reminder.id, self._clock().astimezone(UTC)
                    )

    async def _run(self) -> None:
        while True:
            await self.deliver_due()
            self._wake.clear()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=self._poll_interval)
            except TimeoutError:
                pass
