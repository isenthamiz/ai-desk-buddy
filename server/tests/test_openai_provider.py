"""OpenAI adapter unit tests without network access."""

from types import SimpleNamespace
from typing import Any

import pytest

from aideskbuddy.ai import AIProviderError, ConversationMessage, OpenAIProvider


class FakeResponses:
    def __init__(self, *responses: SimpleNamespace) -> None:
        self.responses = list(responses)
        self.kwargs: dict[str, Any] = {}
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, *responses: SimpleNamespace) -> None:
        self.responses = FakeResponses(*responses)


def text_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(output_text=text, output=[])


@pytest.mark.asyncio
async def test_openai_provider_uses_responses_api_with_conversation_context() -> None:
    client = FakeClient(text_response("  Short answer.  "))
    provider = OpenAIProvider(api_key="test", model="test-model", client=client)  # type: ignore[arg-type]

    reply = await provider.reply(
        [
            ConversationMessage(role="user", content="Hello"),
            ConversationMessage(role="assistant", content="Hi"),
            ConversationMessage(role="user", content="What did I say?"),
        ]
    )

    assert reply == "Short answer."
    assert client.responses.kwargs["model"] == "test-model"
    assert client.responses.kwargs["store"] is False
    assert client.responses.kwargs["input"][-1] == {
        "role": "user",
        "content": "What did I say?",
    }


@pytest.mark.asyncio
async def test_openai_provider_rejects_empty_output() -> None:
    provider = OpenAIProvider(
        api_key="test",
        client=FakeClient(text_response("  ")),  # type: ignore[arg-type]
    )

    with pytest.raises(AIProviderError, match="empty response"):
        await provider.reply([ConversationMessage(role="user", content="Hello")])


@pytest.mark.asyncio
async def test_openai_provider_executes_function_and_returns_output() -> None:
    function_call = SimpleNamespace(
        type="function_call",
        call_id="call-1",
        name="set_timer",
        arguments='{"duration_seconds":30}',
    )
    client = FakeClient(
        SimpleNamespace(output_text="", output=[function_call]),
        text_response("Timer set."),
    )
    provider = OpenAIProvider(api_key="test", client=client)  # type: ignore[arg-type]
    executions: list[tuple[str, dict[str, Any]]] = []

    async def execute(name: str, arguments: dict[str, Any]) -> str:
        executions.append((name, arguments))
        return '{"ok":true}'

    from aideskbuddy.ai import ToolDefinition

    reply = await provider.reply(
        [ConversationMessage(role="user", content="Set a timer")],
        tools=[
            ToolDefinition(
                name="set_timer",
                description="Set a timer",
                parameters={
                    "type": "object",
                    "properties": {"duration_seconds": {"type": "integer"}},
                    "required": ["duration_seconds"],
                    "additionalProperties": False,
                },
            )
        ],
        execute_tool=execute,  # type: ignore[arg-type]
    )

    assert reply == "Timer set."
    assert executions == [("set_timer", {"duration_seconds": 30})]
    assert client.responses.calls[1]["input"][-1] == {
        "type": "function_call_output",
        "call_id": "call-1",
        "output": '{"ok":true}',
    }
