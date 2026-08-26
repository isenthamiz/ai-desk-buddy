"""OpenAI Responses API adapter."""

import json
import logging
from collections.abc import Sequence
from datetime import datetime

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
used tools unless a tool result confirms success. Use the available timer and reminder
tools whenever the user asks to start/cancel a timer or create/cancel a reminder. Pass
For relative reminder requests such as "in one minute", always use
create_relative_reminder and convert the requested delay to seconds; never calculate an
absolute date yourself. Use create_reminder only when the user gives an absolute date or
clock time, passing a timezone-aware ISO 8601 timestamp. Use get_weather for weather
questions and only describe conditions returned by that tool. If a request needs an unavailable
physical or external action, say briefly that you cannot do that yet. Use the Todoist tools
for requests to create, list, or complete Todoist tasks. Always list tasks before completing
an ambiguous reference and use the exact returned task ID. Keep Buddy reminders and Todoist
tasks distinct unless the user explicitly requests both."""


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
                    instructions=(
                        f"{BUDDY_INSTRUCTIONS}\nThe backend's current local date and time "
                        f"is {datetime.now().astimezone().isoformat()}."
                    ),
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
