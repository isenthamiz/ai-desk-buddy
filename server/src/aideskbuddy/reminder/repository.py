"""Reminder persistence boundaries and Supabase adapter."""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from urllib.parse import urlparse

import httpx

from aideskbuddy.reminder.model import Reminder, ReminderStatus


class ReminderRepository(Protocol):
    async def add(self, reminder: Reminder) -> None: ...
    async def cancel(self, reminder_id: str, device_id: str) -> bool: ...
    async def due(self, now: datetime, *, device_id: str | None = None) -> list[Reminder]: ...
    async def mark_delivered(self, reminder_id: str, delivered_at: datetime) -> bool: ...
    async def get(self, reminder_id: str) -> Reminder | None: ...
    async def pending_for_device(self, device_id: str) -> list[Reminder]: ...


class InMemoryReminderRepository:
    """Non-durable repository for tests and unconfigured development."""

    def __init__(self, reminders: Sequence[Reminder] = ()) -> None:
        self._items = {item.id: item for item in reminders}

    async def add(self, reminder: Reminder) -> None:
        self._items[reminder.id] = reminder

    async def cancel(self, reminder_id: str, device_id: str) -> bool:
        item = self._items.get(reminder_id)
        if item is None or item.device_id != device_id or item.status != ReminderStatus.PENDING:
            return False
        self._items[reminder_id] = _replace(item, ReminderStatus.CANCELLED)
        return True

    async def due(self, now: datetime, *, device_id: str | None = None) -> list[Reminder]:
        return sorted(
            (item for item in self._items.values() if item.status == ReminderStatus.PENDING and item.due_at <= now and (device_id is None or item.device_id == device_id)),
            key=lambda item: (item.due_at, item.created_at),
        )

    async def mark_delivered(self, reminder_id: str, delivered_at: datetime) -> bool:
        item = self._items.get(reminder_id)
        if item is None or item.status != ReminderStatus.PENDING:
            return False
        self._items[reminder_id] = _replace(item, ReminderStatus.DELIVERED, delivered_at)
        return True

    async def get(self, reminder_id: str) -> Reminder | None:
        return self._items.get(reminder_id)

    async def pending_for_device(self, device_id: str) -> list[Reminder]:
        return sorted(
            (item for item in self._items.values() if item.device_id == device_id and item.status == ReminderStatus.PENDING),
            key=lambda item: (item.due_at, item.created_at),
        )


class SupabaseReminderRepository:
    def __init__(self, *, base_url: str, secret_key: str, client: httpx.AsyncClient | None = None) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Supabase URL must use HTTPS unless it is local")
        if secret_key.startswith("sb_publishable_"):
            raise ValueError("reminder storage requires an sb_secret_ key")
        if not secret_key.startswith(("sb_secret_", "eyJ")):
            raise ValueError("reminder storage requires an sb_secret_ key or legacy service_role JWT")
        self._base_url = base_url.rstrip("/")
        self._key = secret_key
        self._legacy = secret_key.startswith("eyJ")
        self._client = client

    async def add(self, reminder: Reminder) -> None:
        await self._request("POST", "/rest/v1/buddy_reminders", headers={"Prefer": "return=minimal"}, json=_payload(reminder))

    async def cancel(self, reminder_id: str, device_id: str) -> bool:
        response = await self._request("PATCH", "/rest/v1/buddy_reminders", params={"id": f"eq.{reminder_id}", "device_id": f"eq.{device_id}", "status": "eq.PENDING"}, headers={"Prefer": "return=representation"}, json={"status": "CANCELLED"})
        return bool(response.json())

    async def due(self, now: datetime, *, device_id: str | None = None) -> list[Reminder]:
        params = {"select": "*", "status": "eq.PENDING", "due_at": f"lte.{now.isoformat()}", "order": "due_at.asc,created_at.asc"}
        if device_id is not None:
            params["device_id"] = f"eq.{device_id}"
        return self._rows(await self._request("GET", "/rest/v1/buddy_reminders", params=params))

    async def mark_delivered(self, reminder_id: str, delivered_at: datetime) -> bool:
        response = await self._request("PATCH", "/rest/v1/buddy_reminders", params={"id": f"eq.{reminder_id}", "status": "eq.PENDING"}, headers={"Prefer": "return=representation"}, json={"status": "DELIVERED", "delivered_at": delivered_at.isoformat()})
        return bool(response.json())

    async def get(self, reminder_id: str) -> Reminder | None:
        rows = self._rows(await self._request("GET", "/rest/v1/buddy_reminders", params={"select": "*", "id": f"eq.{reminder_id}", "limit": "1"}))
        return rows[0] if rows else None

    async def pending_for_device(self, device_id: str) -> list[Reminder]:
        return self._rows(await self._request("GET", "/rest/v1/buddy_reminders", params={"select": "*", "device_id": f"eq.{device_id}", "status": "eq.PENDING", "order": "due_at.asc,created_at.asc"}))

    def _rows(self, response: httpx.Response) -> list[Reminder]:
        try:
            return [_from_payload(item) for item in response.json()]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Supabase returned invalid reminders") from exc

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        headers = {"apikey": self._key, **dict(kwargs.pop("headers", {}))}
        if self._legacy:
            headers["Authorization"] = f"Bearer {self._key}"
        try:
            if self._client is not None:
                response = await self._client.request(method, path, headers=headers, **kwargs)
            else:
                async with httpx.AsyncClient(base_url=self._base_url, timeout=15.0) as client:
                    response = await client.request(method, path, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            raise RuntimeError("Supabase reminder service unavailable") from exc


def _payload(item: Reminder) -> dict[str, str | None]:
    return {"id": item.id, "device_id": item.device_id, "text": item.text, "due_at": item.due_at.isoformat(), "status": item.status.value, "created_at": item.created_at.isoformat(), "delivered_at": item.delivered_at.isoformat() if item.delivered_at else None}


def _from_payload(item: dict[str, object]) -> Reminder:
    return Reminder(id=str(item["id"]), device_id=str(item["device_id"]), text=str(item["text"]), due_at=datetime.fromisoformat(str(item["due_at"])), status=ReminderStatus(str(item["status"])), created_at=datetime.fromisoformat(str(item["created_at"])), delivered_at=datetime.fromisoformat(str(item["delivered_at"])) if item.get("delivered_at") else None)


def _replace(item: Reminder, status: ReminderStatus, delivered_at: datetime | None = None) -> Reminder:
    return Reminder(id=item.id, device_id=item.device_id, text=item.text, due_at=item.due_at, status=status, created_at=item.created_at, delivered_at=delivered_at)
