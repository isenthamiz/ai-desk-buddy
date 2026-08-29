"""One-time import of legacy buddy.db reminders into Supabase."""

import argparse
import asyncio
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from aideskbuddy.reminder.model import Reminder
from aideskbuddy.reminder.repository import SupabaseReminderRepository, _from_payload


async def import_reminders(database: Path) -> int:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute("SELECT * FROM reminders")]
    repository = SupabaseReminderRepository(
        base_url=os.environ["BUDDY_SUPABASE_URL"],
        secret_key=os.environ["BUDDY_SUPABASE_SECRET_KEY"],
    )
    for row in rows:
        reminder: Reminder = _from_payload(row)
        if await repository.get(reminder.id) is not None:
            continue
        try:
            await repository.add(reminder)
        except RuntimeError as exc:
            raise RuntimeError(f"could not import reminder {reminder.id}") from exc
    return len(rows)


def main() -> None:
    load_dotenv(Path(__file__).parents[1] / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    count = asyncio.run(import_reminders(args.database))
    print(f"Imported {count} reminders.")


if __name__ == "__main__":
    main()
