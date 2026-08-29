"""Tests for the private note-server client boundary."""

import httpx
import pytest

from aideskbuddy.notes import NotesClient, NotesError


def test_notes_client_rejects_non_loopback_service() -> None:
    with pytest.raises(ValueError, match="loopback"):
        NotesClient(base_url="https://notes.example.com", token="secret")


@pytest.mark.asyncio
async def test_notes_client_sends_token_and_returns_answer_with_citations() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret"
        assert request.url.path == "/v1/query"
        assert request.content == b'{"question":"What display?"}'
        return httpx.Response(
            200,
            json={"answer": "Use SSD1306.", "citations": ["[[Hardware#Display]]"]},
        )

    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8010",
        transport=httpx.MockTransport(handler),
    ) as http_client:
        client = NotesClient(
            base_url="http://127.0.0.1:8010", token="secret", client=http_client
        )
        answer = await client.answer("What display?")

    assert answer == "Use SSD1306.\n\nSources: [[Hardware#Display]]"


@pytest.mark.asyncio
async def test_notes_client_hides_upstream_errors() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "internal detail"})

    async with httpx.AsyncClient(
        base_url="http://localhost:8010",
        transport=httpx.MockTransport(handler),
    ) as http_client:
        client = NotesClient(
            base_url="http://localhost:8010", token="secret", client=http_client
        )
        with pytest.raises(NotesError, match="request failed"):
            await client.answer("question")
