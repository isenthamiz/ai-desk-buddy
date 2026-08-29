"""Tests for durable reminder behavior and Supabase persistence."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from aideskbuddy.reminder import (
    InMemoryReminderRepository,
    Reminder,
    ReminderService,
    ReminderStatus,
    SupabaseReminderRepository,
)


@pytest.mark.asyncio
async def test_reminder_is_delivered_once_after_service_restart() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    delivered = []

    async def notify(reminder):
        delivered.append(reminder)
        return True

    repository = InMemoryReminderRepository()
    first_service = ReminderService(repository, notify, clock=lambda: now)
    reminder = await first_service.create(
        "simulator-001", "Join the design review", now + timedelta(minutes=5)
    )
    restarted_service = ReminderService(
        repository, notify, clock=lambda: now + timedelta(minutes=6)
    )
    await restarted_service.deliver_due()
    await restarted_service.deliver_due()

    assert [item.id for item in delivered] == [reminder.id]
    stored = await repository.get(reminder.id)
    assert stored is not None and stored.status is ReminderStatus.DELIVERED


@pytest.mark.asyncio
async def test_offline_reminder_stays_pending_until_device_reconnects() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    online = False

    async def notify(_reminder):
        return online

    repository = InMemoryReminderRepository()
    service = ReminderService(repository, notify, clock=lambda: now)
    reminder = await service.create(
        "simulator-001", "Stretch", now - timedelta(seconds=1)
    )
    await service.deliver_due()
    assert (await repository.get(reminder.id)).status is ReminderStatus.PENDING  # type: ignore[union-attr]
    online = True
    await service.deliver_due("simulator-001")
    assert (await repository.get(reminder.id)).status is ReminderStatus.DELIVERED  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_cancel_and_validation() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)

    async def notify(_reminder):
        return True

    repository = InMemoryReminderRepository()
    service = ReminderService(repository, notify, clock=lambda: now)
    reminder = await service.create(
        "simulator-001", "Stretch", now + timedelta(hours=1)
    )
    assert await service.cancel("simulator-001", reminder.id)
    assert not await service.cancel("another-device", reminder.id)
    with pytest.raises(ValueError, match="UTC offset"):
        await service.create(
            "simulator-001", "Stretch", datetime(2026, 8, 24, 12, 0)
        )


@pytest.mark.asyncio
async def test_relative_reminder_uses_backend_clock() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)

    async def notify(_reminder):
        return True

    service = ReminderService(InMemoryReminderRepository(), notify, clock=lambda: now)
    reminder = await service.create_in("simulator-001", "Stretch", 60)
    assert reminder.due_at == now + timedelta(minutes=1)


@pytest.mark.asyncio
async def test_supabase_repository_uses_server_key_and_parses_rows() -> None:
    requests: list[httpx.Request] = []
    reminder = Reminder(
        id="00000000-0000-0000-0000-000000000001",
        device_id="simulator-001",
        text="Stretch",
        due_at=datetime(2026, 8, 24, 13, 0, tzinfo=UTC),
        status=ReminderStatus.PENDING,
        created_at=datetime(2026, 8, 24, 12, 0, tzinfo=UTC),
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(201)
        return httpx.Response(200, json=[{
            "id": reminder.id, "device_id": reminder.device_id,
            "text": reminder.text, "due_at": reminder.due_at.isoformat(),
            "status": reminder.status.value,
            "created_at": reminder.created_at.isoformat(), "delivered_at": None,
        }])

    async with httpx.AsyncClient(
        base_url="https://example.supabase.co",
        transport=httpx.MockTransport(handler),
    ) as client:
        repository = SupabaseReminderRepository(
            base_url="https://example.supabase.co",
            secret_key="sb_secret_test",
            client=client,
        )
        await repository.add(reminder)
        assert (await repository.pending_for_device("simulator-001"))[0] == reminder

    assert requests[0].headers["apikey"] == "sb_secret_test"
    assert "Authorization" not in requests[0].headers


def test_reminder_migration_grants_only_server_role() -> None:
    migration = (
        Path(__file__).parents[1] / "supabase" / "reminders.sql"
    ).read_text(encoding="utf-8")

    assert "REVOKE ALL ON public.buddy_reminders FROM anon, authenticated" in migration
    assert "ON public.buddy_reminders TO service_role" in migration
