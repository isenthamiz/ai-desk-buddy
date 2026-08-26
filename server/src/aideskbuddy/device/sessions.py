"""In-memory connected-device sessions for Milestone 1."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import WebSocket

from aideskbuddy.protocol import BuddyState, ServerMessage, UserText

MessageSender = Callable[[list[ServerMessage]], Awaitable[None]]
TextHandler = Callable[[UserText], Awaitable[None]]
TimerStarter = Callable[[int], Awaitable[bool]]
TimerCanceller = Callable[[], Awaitable[bool]]


@dataclass(slots=True)
class DeviceSession:
    device_id: str
    device_type: str
    websocket: WebSocket
    send: MessageSender
    send_text: TextHandler
    start_timer: TimerStarter
    cancel_timer: TimerCanceller
    state: BuddyState = BuddyState.IDLE
    timer_duration_seconds: int | None = None


class SessionRegistry:
    """Track currently connected devices without persistence."""

    def __init__(self) -> None:
        self._sessions: dict[str, DeviceSession] = {}

    def connect(self, session: DeviceSession) -> None:
        self._sessions[session.device_id] = session

    def disconnect(self, session: DeviceSession) -> None:
        if self._sessions.get(session.device_id) is session:
            self._sessions.pop(session.device_id, None)

    def get(self, device_id: str) -> DeviceSession | None:
        return self._sessions.get(device_id)

    def all(self) -> tuple[DeviceSession, ...]:
        return tuple(self._sessions.values())

    def __len__(self) -> int:
        return len(self._sessions)
