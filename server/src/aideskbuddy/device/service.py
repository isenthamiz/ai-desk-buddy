"""Deterministic Milestone 1 device behavior."""

from aideskbuddy.protocol import (
    BuddyState,
    ButtonPressed,
    DeviceConnected,
    DeviceMessage,
    DisplayText,
    PresenceChanged,
    ServerMessage,
    Speak,
    StateChanged,
    UserText,
)


def initial_messages(_message: DeviceConnected) -> list[ServerMessage]:
    return [StateChanged(state=BuddyState.IDLE)]


def handle_device_message(message: DeviceMessage) -> list[ServerMessage]:
    """Return simple deterministic reactions for simulator events."""
    if isinstance(message, UserText):
        response = f"Echo: {message.text}"
        return [
            DisplayText(text=response, request_id=message.request_id),
            Speak(text=response, request_id=message.request_id),
        ]
    if isinstance(message, ButtonPressed):
        return [StateChanged(state=BuddyState.LISTENING)]
    if isinstance(message, PresenceChanged):
        state = BuddyState.IDLE if message.present else BuddyState.SLEEPING
        return [StateChanged(state=state)]
    return []
