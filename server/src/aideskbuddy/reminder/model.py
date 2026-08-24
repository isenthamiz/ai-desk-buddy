"""Reminder domain values."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ReminderStatus(StrEnum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class Reminder:
    id: str
    device_id: str
    text: str
    due_at: datetime
    status: ReminderStatus
    created_at: datetime
    delivered_at: datetime | None = None

    def __post_init__(self) -> None:
        for value in (self.due_at, self.created_at, self.delivered_at):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError("reminder timestamps must be timezone-aware")

    @staticmethod
    def utc(value: datetime) -> datetime:
        return value.astimezone(UTC)
