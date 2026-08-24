"""In-memory connected-device sessions for Milestone 1."""

from dataclasses import dataclass

from fastapi import WebSocket


@dataclass(frozen=True, slots=True)
class DeviceSession:
    device_id: str
    device_type: str
    websocket: WebSocket


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

    def __len__(self) -> int:
        return len(self._sessions)
