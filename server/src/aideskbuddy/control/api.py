"""Browser-facing control API kept separate from the device protocol."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from aideskbuddy.device.sessions import DeviceSession, SessionRegistry
from aideskbuddy.protocol import ReminderCancelled, ReminderCreated, UserText
from aideskbuddy.reminder import Reminder, ReminderRepository, ReminderService

class TimerRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    duration_seconds: int = Field(alias="durationSeconds", gt=0, le=86_400)


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2_000)

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text must not be blank")
        return value


class ReminderRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    text: str = Field(min_length=1, max_length=500)
    due_at: datetime = Field(alias="dueAt")

    @field_validator("text")
    @classmethod
    def reject_blank_reminder(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text must not be blank")
        return value

    @field_validator("due_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dueAt must include a UTC offset")
        return value


def _reminder_payload(reminder: Reminder) -> dict[str, str]:
    return {
        "id": reminder.id,
        "text": reminder.text,
        "dueAt": reminder.due_at.isoformat(),
        "status": reminder.status.value,
    }


def create_control_router(
    sessions: SessionRegistry,
    reminders: ReminderService,
    repository: ReminderRepository,
    device_id: str,
) -> APIRouter:
    router = APIRouter()

    def connected_session() -> DeviceSession:
        session = sessions.get(device_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Buddy {device_id} is offline",
            )
        return session

    @router.get("/api/control/status")
    async def control_status() -> dict[str, object]:
        session = sessions.get(device_id)
        return {
            "backend": "online",
            "device": {
                "id": device_id,
                "type": session.device_type if session else None,
                "connected": session is not None,
                "state": session.state.value if session else "OFFLINE",
            },
            "timer": {
                "active": bool(session and session.timer_duration_seconds is not None),
                "durationSeconds": (
                    session.timer_duration_seconds if session else None
                ),
            },
        }

    @router.post("/api/control/messages", status_code=status.HTTP_202_ACCEPTED)
    async def send_text(request: TextRequest) -> dict[str, bool]:
        await connected_session().send_text(UserText(text=request.text))
        return {"ok": True}

    @router.post("/api/control/timers", status_code=status.HTTP_201_CREATED)
    async def start_timer(request: TimerRequest) -> dict[str, object]:
        started = await connected_session().start_timer(request.duration_seconds)
        if not started:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A timer is already active",
            )
        return {"ok": True, "durationSeconds": request.duration_seconds}

    @router.delete("/api/control/timers/current")
    async def cancel_timer() -> dict[str, bool]:
        cancelled = await connected_session().cancel_timer()
        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="There is no active timer",
            )
        return {"ok": True}

    @router.get("/api/control/reminders")
    async def list_reminders() -> dict[str, object]:
        items = await repository.pending_for_device(device_id)
        return {"items": [_reminder_payload(item) for item in items]}

    @router.post("/api/control/reminders", status_code=status.HTTP_201_CREATED)
    async def create_reminder(request: ReminderRequest) -> dict[str, str]:
        reminder = await reminders.create(device_id, request.text, request.due_at)
        session = sessions.get(device_id)
        if session is not None:
            await session.send(
                [
                    ReminderCreated(
                        reminderId=reminder.id,
                        text=reminder.text,
                        dueAt=reminder.due_at,
                    )
                ]
            )
        return _reminder_payload(reminder)

    @router.delete("/api/control/reminders/{reminder_id}")
    async def cancel_reminder(reminder_id: str) -> dict[str, bool]:
        if not await reminders.cancel(device_id, reminder_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending reminder not found",
            )
        session = sessions.get(device_id)
        if session is not None:
            await session.send([ReminderCancelled(reminderId=reminder_id)])
        return {"ok": True}

    return router
