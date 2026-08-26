"""WebSocket adapter for connected devices."""

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from aideskbuddy.ai import AIProvider
from aideskbuddy.conversation import ConversationService
from aideskbuddy.device.service import (
    handle_device_message,
    handle_user_text,
    initial_messages,
)
from aideskbuddy.device.sessions import DeviceSession, SessionRegistry
from aideskbuddy.protocol import (
    BuddyState,
    ButtonPressed,
    DeviceConnected,
    DisplayText,
    ProtocolMessageError,
    ServerMessage,
    Speak,
    StateChanged,
    TimerCompleted,
    TimerCancelled,
    TimerStarted,
    UserText,
    parse_device_message,
)
from aideskbuddy.timer import TimerService
from aideskbuddy.todoist import TodoistService
from aideskbuddy.tools import ToolRegistry
from aideskbuddy.reminder import ReminderService
from aideskbuddy.weather import WeatherService

LOGGER = logging.getLogger(__name__)


async def handle_device_websocket(
    websocket: WebSocket,
    sessions: SessionRegistry,
    ai_provider: AIProvider,
    reminders: ReminderService,
    weather: WeatherService | None = None,
    todoist: TodoistService | None = None,
) -> None:
    """Handle one authenticated-by-handshake device connection."""
    await websocket.accept()
    session: DeviceSession | None = None
    send_lock = asyncio.Lock()
    timer: TimerService | None = None

    async def send(messages: list[ServerMessage]) -> None:
        async with send_lock:
            await _send_messages(websocket, messages)

    async def timer_completed() -> None:
        alert = "Your timer has finished."
        await send(
            [
                TimerCompleted(),
                StateChanged(state=BuddyState.ALERT),
                DisplayText(text=alert),
                Speak(text=alert),
                StateChanged(state=BuddyState.IDLE),
            ]
        )
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
            send=send,
        )
        sessions.connect(session)
        LOGGER.info("Device connected: %s", session.device_id)
        await send(initial_messages(first_message))
        timer = TimerService(timer_completed)
        tools = ToolRegistry(timer, reminders, session.device_id, weather, todoist)
        conversation = ConversationService(ai_provider, tools, send)
        await reminders.deliver_due(session.device_id)

        while True:
            payload = await websocket.receive_text()
            try:
                message = parse_device_message(payload)
            except ProtocolMessageError as exc:
                LOGGER.warning("Ignoring invalid device message: %s", exc)
                continue
            if isinstance(message, UserText):
                await send(
                    [StateChanged(state=BuddyState.THINKING, request_id=message.request_id)],
                )
                response_messages = await handle_user_text(message, conversation)
                if timer.is_active:
                    response_messages[-1] = StateChanged(
                        state=BuddyState.TIMER,
                        request_id=message.request_id,
                    )
                await send(response_messages)
            elif (
                isinstance(message, ButtonPressed)
                and message.button == "TIMER_START"
                and message.duration_seconds is not None
            ):
                if timer.start(message.duration_seconds):
                    await send(
                        [
                            TimerStarted(duration_seconds=message.duration_seconds),
                            StateChanged(state=BuddyState.TIMER),
                        ]
                    )
            elif isinstance(message, ButtonPressed) and message.button == "TIMER_CANCEL":
                if timer.cancel():
                    await send(
                        [TimerCancelled(), StateChanged(state=BuddyState.IDLE)]
                    )
            else:
                await send(handle_device_message(message))
    except WebSocketDisconnect:
        pass
    finally:
        if timer is not None:
            await timer.close()
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
