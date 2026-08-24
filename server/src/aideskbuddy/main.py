"""FastAPI application entry point."""

from fastapi import FastAPI, WebSocket

from aideskbuddy.device.sessions import SessionRegistry
from aideskbuddy.device.websocket import handle_device_websocket


def create_app() -> FastAPI:
    """Create and configure the backend application."""
    application = FastAPI(title="AI Desk Buddy")
    application.state.sessions = SessionRegistry()

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.websocket("/ws/device")
    async def device_socket(websocket: WebSocket) -> None:
        await handle_device_websocket(websocket, application.state.sessions)

    return application


app = create_app()
