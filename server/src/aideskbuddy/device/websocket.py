"""WebSocket adapter for connected devices."""

import logging

from fastapi import WebSocket, WebSocketDisconnect

from aideskbuddy.device.service import handle_device_message, initial_messages
from aideskbuddy.device.sessions import DeviceSession, SessionRegistry
from aideskbuddy.protocol import (
    DeviceConnected,
    ProtocolMessageError,
    ServerMessage,
    parse_device_message,
)

LOGGER = logging.getLogger(__name__)


async def handle_device_websocket(
    websocket: WebSocket,
    sessions: SessionRegistry,
) -> None:
    """Handle one authenticated-by-handshake device connection."""
    await websocket.accept()
    session: DeviceSession | None = None
    try:
        try:
            first_message = parse_device_message(await websocket.receive_text())
        except ProtocolMessageError:
            await websocket.close(code=1008, reason="DEVICE_CONNECTED required")
            return

        if not isinstance(first_message, DeviceConnected):
            await websocket.close(code=1008, reason="DEVICE_CONNECTED required")
            return

        session = DeviceSession(
            device_id=first_message.device_id,
            device_type=first_message.device_type,
            websocket=websocket,
        )
        sessions.connect(session)
        LOGGER.info("Device connected: %s", session.device_id)
        await _send_messages(websocket, initial_messages(first_message))

        while True:
            payload = await websocket.receive_text()
            try:
                message = parse_device_message(payload)
            except ProtocolMessageError as exc:
                LOGGER.warning("Ignoring invalid device message: %s", exc)
                continue
            await _send_messages(websocket, handle_device_message(message))
    except WebSocketDisconnect:
        pass
    finally:
        if session is not None:
            sessions.disconnect(session)
            LOGGER.info("Device disconnected: %s", session.device_id)


async def _send_messages(
    websocket: WebSocket,
    messages: list[ServerMessage],
) -> None:
    for message in messages:
        await websocket.send_json(
            message.model_dump(mode="json", by_alias=True, exclude_none=True)
        )
