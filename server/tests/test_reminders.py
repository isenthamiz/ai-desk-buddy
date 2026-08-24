"""Tests for durable reminder behavior."""

from datetime import UTC, datetime, timedelta

import pytest

from aideskbuddy.reminder import (
    ReminderService,
    ReminderStatus,
    SQLiteReminderRepository,
)


@pytest.mark.asyncio
async def test_reminder_persists_and_is_delivered_once(tmp_path) -> None:
    database = tmp_path / "buddy.db"
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    delivered = []

    async def notify(reminder):
        delivered.append(reminder)
        return True

    first_repository = SQLiteReminderRepository(database)
    first_service = ReminderService(first_repository, notify, clock=lambda: now)
    reminder = first_service.create(
        "simulator-001", "Join the design review", now + timedelta(minutes=5)
    )

    restarted_repository = SQLiteReminderRepository(database)
    restarted_service = ReminderService(
        restarted_repository,
        notify,
        clock=lambda: now + timedelta(minutes=6),
    )
    await restarted_service.deliver_due()
    await restarted_service.deliver_due()

    assert [item.id for item in delivered] == [reminder.id]
    stored = restarted_repository.get(reminder.id)
    assert stored is not None
    assert stored.status is ReminderStatus.DELIVERED


@pytest.mark.asyncio
async def test_offline_reminder_stays_pending_until_device_reconnects(tmp_path) -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    online = False

    async def notify(_reminder):
        return online

    repository = SQLiteReminderRepository(tmp_path / "buddy.db")
    service = ReminderService(repository, notify, clock=lambda: now)
    reminder = service.create("simulator-001", "Stretch", now - timedelta(seconds=1))

    await service.deliver_due()
    assert repository.get(reminder.id).status is ReminderStatus.PENDING

    online = True
    await service.deliver_due("simulator-001")
    assert repository.get(reminder.id).status is ReminderStatus.DELIVERED


def test_cancelled_reminder_survives_restart(tmp_path) -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)

    async def notify(_reminder):
        return True

    database = tmp_path / "buddy.db"
    service = ReminderService(
        SQLiteReminderRepository(database), notify, clock=lambda: now
    )
    reminder = service.create("simulator-001", "Stretch", now + timedelta(hours=1))

    assert service.cancel("simulator-001", reminder.id)
    assert not service.cancel("another-device", reminder.id)
    stored = SQLiteReminderRepository(database).get(reminder.id)
    assert stored is not None
    assert stored.status is ReminderStatus.CANCELLED


def test_reminder_requires_timezone_aware_due_time(tmp_path) -> None:
    async def notify(_reminder):
        return True

    service = ReminderService(SQLiteReminderRepository(tmp_path / "buddy.db"), notify)
    with pytest.raises(ValueError, match="UTC offset"):
        service.create("simulator-001", "Stretch", datetime(2026, 8, 24, 12, 0))


def test_relative_reminder_uses_backend_clock(tmp_path) -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)

    async def notify(_reminder):
        return True

    service = ReminderService(
        SQLiteReminderRepository(tmp_path / "buddy.db"), notify, clock=lambda: now
    )
    reminder = service.create_in("simulator-001", "Stretch", 60)

    assert reminder.due_at == now + timedelta(minutes=1)
