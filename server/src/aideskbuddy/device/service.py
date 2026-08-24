"""Device behavior and conversational response mapping."""

from aideskbuddy.ai import AIProviderError
from aideskbuddy.conversation import ConversationService

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
    if isinstance(message, ButtonPressed):
        return [StateChanged(state=BuddyState.LISTENING)]
    if isinstance(message, PresenceChanged):
        state = BuddyState.IDLE if message.present else BuddyState.SLEEPING
        return [StateChanged(state=state)]
    return []


async def handle_user_text(
    message: UserText,
    conversation: ConversationService,
    *,
    return_state: BuddyState = BuddyState.IDLE,
) -> list[ServerMessage]:
    """Generate a conversational reply and map it to device messages."""
    try:
        response = await conversation.respond(message.text)
    except AIProviderError:
        apology = "Sorry, I couldn't think of a response just now. Please try again."
        return [
            StateChanged(state=BuddyState.ERROR, request_id=message.request_id),
            DisplayText(text=apology, request_id=message.request_id),
            Speak(text=apology, request_id=message.request_id),
            StateChanged(state=return_state, request_id=message.request_id),
        ]

    return [
        StateChanged(state=BuddyState.SPEAKING, request_id=message.request_id),
        DisplayText(text=response, request_id=message.request_id),
        Speak(text=response, request_id=message.request_id),
        StateChanged(state=return_state, request_id=message.request_id),
    ]
