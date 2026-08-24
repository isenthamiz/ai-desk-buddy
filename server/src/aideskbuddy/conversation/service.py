"""Provider-neutral, in-memory conversation orchestration."""

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from aideskbuddy.ai import AIProvider, ConversationMessage
from aideskbuddy.protocol import ServerMessage
from aideskbuddy.tools import ToolRegistry

ToolMessageHandler = Callable[[list[ServerMessage]], Awaitable[None]]


class ConversationService:
    """Maintain a bounded conversation history for one connected device."""

    def __init__(
        self,
        provider: AIProvider,
        tools: ToolRegistry,
        send_tool_messages: ToolMessageHandler,
        *,
        max_messages: int = 20,
    ) -> None:
        self._provider = provider
        self._tools = tools
        self._send_tool_messages = send_tool_messages
        self._max_messages = max_messages
        self._messages: list[ConversationMessage] = []

    async def respond(self, user_text: str) -> str:
        pending = [*self._messages, ConversationMessage(role="user", content=user_text)]

        async def execute_tool(name: str, arguments: Mapping[str, Any]) -> str:
            result = await self._tools.execute(name, arguments)
            await self._send_tool_messages(list(result.messages))
            return result.output

        reply = await self._provider.reply(
            pending,
            tools=self._tools.definitions,
            execute_tool=execute_tool,
        )
        self._messages = [
            *pending,
            ConversationMessage(role="assistant", content=reply),
        ][-self._max_messages :]
        return reply
