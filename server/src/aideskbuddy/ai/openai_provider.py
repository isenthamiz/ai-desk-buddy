"""OpenAI Responses API adapter."""

import json
import logging
from collections.abc import Sequence

import openai
from openai import AsyncOpenAI

from aideskbuddy.ai.provider import (
    AIProviderError,
    ConversationMessage,
    ToolDefinition,
    ToolExecutor,
)

LOGGER = logging.getLogger(__name__)

BUDDY_INSTRUCTIONS = """You are Buddy, a friendly physical companion on the user's desk.
Answer conversationally and helpfully. Keep replies concise—normally one or two short
sentences—because they will be spoken aloud. Do not claim to have performed actions or
used tools unless a tool result confirms success. Use the available timer tools whenever
the user asks to start or cancel a timer. If a request needs an unavailable physical or
external action, say briefly that you cannot do that yet."""


class OpenAIProvider:
    """Generate Buddy replies with OpenAI's async Responses API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-5.6-luna",
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._client = client or AsyncOpenAI(api_key=api_key, timeout=30.0, max_retries=2)
        self._model = model

    async def reply(
        self,
        messages: Sequence[ConversationMessage],
        *,
        tools: Sequence[ToolDefinition] = (),
        execute_tool: ToolExecutor | None = None,
    ) -> str:
        input_items: list[object] = [
            {"role": message.role, "content": message.content} for message in messages
        ]
        response_tools = [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": dict(tool.parameters),
                "strict": True,
            }
            for tool in tools
        ]
        try:
            for _ in range(4):
                response = await self._client.responses.create(
                    model=self._model,
                    instructions=BUDDY_INSTRUCTIONS,
                    input=input_items,
                    tools=response_tools,
                    max_output_tokens=200,
                    reasoning={"effort": "none"},
                    store=False,
                )
                calls = [
                    item for item in response.output if item.type == "function_call"
                ]
                if not calls:
                    reply = response.output_text.strip()
                    if not reply:
                        raise AIProviderError("OpenAI returned an empty response")
                    return reply
                if execute_tool is None:
                    raise AIProviderError("OpenAI requested a tool without an executor")

                input_items.extend(response.output)
                for call in calls:
                    try:
                        arguments = json.loads(call.arguments)
                        if not isinstance(arguments, dict):
                            raise ValueError("arguments must be an object")
                        result = await execute_tool(call.name, arguments)
                    except (json.JSONDecodeError, ValueError) as exc:
                        result = json.dumps({"ok": False, "error": str(exc)})
                    input_items.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": result,
                        }
                    )
        except openai.OpenAIError as exc:
            request_id = getattr(exc, "request_id", None)
            LOGGER.exception("OpenAI request failed (request_id=%s)", request_id)
            raise AIProviderError("OpenAI request failed") from exc

        raise AIProviderError("OpenAI exceeded the tool-call limit")
