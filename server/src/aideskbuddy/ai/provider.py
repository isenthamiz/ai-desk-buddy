"""Provider-neutral AI conversation boundary."""

from dataclasses import dataclass
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Literal, Protocol, Sequence


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    role: Literal["user", "assistant"]
    content: str


class AIProviderError(RuntimeError):
    """Raised when an AI provider cannot produce a usable reply."""


class AIProvider(Protocol):
    async def reply(
        self,
        messages: Sequence[ConversationMessage],
        *,
        tools: Sequence["ToolDefinition"] = (),
        execute_tool: "ToolExecutor | None" = None,
    ) -> str:
        """Generate a reply using the supplied conversation context."""


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: Mapping[str, Any]


ToolExecutor = Callable[[str, Mapping[str, Any]], Awaitable[str]]


class UnavailableAIProvider:
    """Graceful provider used when the server has no API credentials."""

    async def reply(
        self,
        messages: Sequence[ConversationMessage],
        *,
        tools: Sequence[ToolDefinition] = (),
        execute_tool: ToolExecutor | None = None,
    ) -> str:
        del tools, execute_tool
        del messages
        raise AIProviderError("AI provider is not configured")
