"""FastAPI application entry point."""

import os
from pathlib import Path

from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv

from aideskbuddy.ai import AIProvider, OpenAIProvider, UnavailableAIProvider
from aideskbuddy.device.sessions import SessionRegistry
from aideskbuddy.device.websocket import handle_device_websocket

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


def create_app(*, ai_provider: AIProvider | None = None) -> FastAPI:
    """Create and configure the backend application."""
    application = FastAPI(title="AI Desk Buddy")
    application.state.sessions = SessionRegistry()
    application.state.ai_provider = ai_provider or _ai_provider_from_environment()

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.websocket("/ws/device")
    async def device_socket(websocket: WebSocket) -> None:
        await handle_device_websocket(
            websocket,
            application.state.sessions,
            application.state.ai_provider,
        )

    return application


app = create_app()
