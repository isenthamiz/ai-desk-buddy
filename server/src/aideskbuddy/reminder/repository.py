"""SQLite persistence for reminders."""

import sqlite3
from datetime import datetime
from pathlib import Path

from aideskbuddy.reminder.model import Reminder, ReminderStatus


class SQLiteReminderRepository:
    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER NOT NULL
                );
                INSERT INTO schema_version(version)
                SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_version);
                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    delivered_at TEXT
                );
                CREATE INDEX IF NOT EXISTS reminders_pending_due
                ON reminders(status, due_at);
                """
            )

    def add(self, reminder: Reminder) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO reminders
                (id, device_id, text, due_at, status, created_at, delivered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    reminder.id,
                    reminder.device_id,
                    reminder.text,
                    reminder.due_at.isoformat(),
                    reminder.status.value,
                    reminder.created_at.isoformat(),
                    None,
                ),
            )

    def cancel(self, reminder_id: str, device_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE reminders SET status = ?
                WHERE id = ? AND device_id = ? AND status = ?""",
                (
                    ReminderStatus.CANCELLED.value,
                    reminder_id,
                    device_id,
                    ReminderStatus.PENDING.value,
                ),
            )
            return cursor.rowcount == 1

    def due(self, now: datetime, *, device_id: str | None = None) -> list[Reminder]:
        query = "SELECT * FROM reminders WHERE status = ? AND due_at <= ?"
        params: list[str] = [ReminderStatus.PENDING.value, now.isoformat()]
        if device_id is not None:
            query += " AND device_id = ?"
            params.append(device_id)
        query += " ORDER BY due_at, created_at"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._from_row(row) for row in rows]

    def mark_delivered(self, reminder_id: str, delivered_at: datetime) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE reminders SET status = ?, delivered_at = ?
                WHERE id = ? AND status = ?""",
                (
                    ReminderStatus.DELIVERED.value,
                    delivered_at.isoformat(),
                    reminder_id,
                    ReminderStatus.PENDING.value,
                ),
            )
            return cursor.rowcount == 1

    def get(self, reminder_id: str) -> Reminder | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
            ).fetchone()
        return None if row is None else self._from_row(row)

    def pending_for_device(self, device_id: str) -> list[Reminder]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM reminders
                WHERE device_id = ? AND status = ?
                ORDER BY due_at, created_at""",
                (device_id, ReminderStatus.PENDING.value),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Reminder:
        return Reminder(
            id=row["id"],
            device_id=row["device_id"],
            text=row["text"],
            due_at=datetime.fromisoformat(row["due_at"]),
            status=ReminderStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            delivered_at=(
                datetime.fromisoformat(row["delivered_at"])
                if row["delivered_at"]
                else None
            ),
        )
