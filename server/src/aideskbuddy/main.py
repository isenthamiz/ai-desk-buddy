"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv

from aideskbuddy.ai import AIProvider, OpenAIProvider, UnavailableAIProvider
from aideskbuddy.device.sessions import SessionRegistry
from aideskbuddy.device.websocket import handle_device_websocket
from aideskbuddy.protocol import BuddyState, DisplayText, ReminderDue, Speak, StateChanged
from aideskbuddy.reminder import Reminder, ReminderService, SQLiteReminderRepository

SERVER_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(SERVER_ROOT / ".env")


def _ai_provider_from_environment() -> AIProvider:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return UnavailableAIProvider()
    return OpenAIProvider(
        api_key=api_key,
        model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
    )


def create_app(
    *,
    ai_provider: AIProvider | None = None,
    database_path: str | Path | None = None,
    reminder_poll_interval: float = 1.0,
) -> FastAPI:
    """Create and configure the backend application."""
    sessions = SessionRegistry()

    async def notify(reminder: Reminder) -> bool:
        session = sessions.get(reminder.device_id)
        if session is None:
            return False
        await session.send(
            [
                StateChanged(state=BuddyState.ALERT),
                ReminderDue(
                    reminderId=reminder.id,
                    text=reminder.text,
                    dueAt=reminder.due_at,
                ),
                DisplayText(text=reminder.text),
                Speak(text=reminder.text),
                StateChanged(state=BuddyState.IDLE),
            ]
        )
        return True

    resolved_database_path = database_path or os.getenv(
        "BUDDY_DATABASE_PATH", str(SERVER_ROOT / "data" / "buddy.db")
    )
    if str(resolved_database_path) != ":memory:":
        Path(resolved_database_path).parent.mkdir(parents=True, exist_ok=True)
    repository = SQLiteReminderRepository(resolved_database_path)
    reminders = ReminderService(
        repository, notify, poll_interval=reminder_poll_interval
    )

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        reminders.start()
        try:
            yield
        finally:
            await reminders.close()

    application = FastAPI(title="AI Desk Buddy", lifespan=lifespan)
    application.state.sessions = sessions
    application.state.ai_provider = ai_provider or _ai_provider_from_environment()
    application.state.reminders = reminders
    application.state.reminder_repository = repository

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.websocket("/ws/device")
    async def device_socket(websocket: WebSocket) -> None:
        await handle_device_websocket(
            websocket,
            application.state.sessions,
            application.state.ai_provider,
            application.state.reminders,
        )

    return application


app = create_app()
