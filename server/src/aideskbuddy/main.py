"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from aideskbuddy.ai import AIProvider, OpenAIProvider, UnavailableAIProvider
from aideskbuddy.control import create_control_router
from aideskbuddy.device.sessions import SessionRegistry
from aideskbuddy.device.websocket import handle_device_websocket
from aideskbuddy.protocol import BuddyState, DisplayText, ReminderDue, Speak, StateChanged
from aideskbuddy.reminder import Reminder, ReminderService, SQLiteReminderRepository
from aideskbuddy.todoist import TodoistRestProvider, TodoistService
from aideskbuddy.weather import OpenMeteoWeatherProvider, WeatherService

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


def _weather_service_from_environment() -> WeatherService | None:
    latitude = os.getenv("BUDDY_WEATHER_LATITUDE")
    longitude = os.getenv("BUDDY_WEATHER_LONGITUDE")
    location_name = os.getenv("BUDDY_WEATHER_LOCATION_NAME")
    timezone = os.getenv("BUDDY_WEATHER_TIMEZONE")
    values = (latitude, longitude, location_name, timezone)
    if not any(values):
        return None
    if not all(values):
        raise ValueError(
            "weather requires BUDDY_WEATHER_LATITUDE, BUDDY_WEATHER_LONGITUDE, "
            "BUDDY_WEATHER_LOCATION_NAME, and BUDDY_WEATHER_TIMEZONE"
        )
    try:
        parsed_latitude = float(latitude)
        parsed_longitude = float(longitude)
    except (TypeError, ValueError) as exc:
        raise ValueError("weather latitude and longitude must be numbers") from exc
    if not -90 <= parsed_latitude <= 90:
        raise ValueError("weather latitude must be between -90 and 90")
    if not -180 <= parsed_longitude <= 180:
        raise ValueError("weather longitude must be between -180 and 180")
    return WeatherService(
        OpenMeteoWeatherProvider(
            latitude=parsed_latitude,
            longitude=parsed_longitude,
            location_name=str(location_name),
            timezone=str(timezone),
        )
    )


def _todoist_service_from_environment() -> TodoistService | None:
    token = os.getenv("TODOIST_API_TOKEN")
    if not token:
        return None
    return TodoistService(TodoistRestProvider(token=token))


def _control_origins_from_environment() -> list[str]:
    configured = os.getenv("BUDDY_CONTROL_ALLOWED_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return ["http://localhost:8081", "http://127.0.0.1:8081"]


def create_app(
    *,
    ai_provider: AIProvider | None = None,
    database_path: str | Path | None = None,
    reminder_poll_interval: float = 1.0,
    weather_service: WeatherService | None = None,
    todoist_service: TodoistService | None = None,
    control_device_id: str | None = None,
    control_allowed_origins: list[str] | None = None,
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
    application.state.weather = weather_service or _weather_service_from_environment()
    application.state.todoist = todoist_service or _todoist_service_from_environment()
    application.state.control_device_id = control_device_id or os.getenv(
        "BUDDY_CONTROL_DEVICE_ID", "simulator-001"
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=(
            control_allowed_origins
            if control_allowed_origins is not None
            else _control_origins_from_environment()
        ),
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )
    application.include_router(
        create_control_router(
            sessions,
            reminders,
            repository,
            application.state.control_device_id,
        )
    )

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
            application.state.weather,
            application.state.todoist,
        )

    return application


app = create_app()
