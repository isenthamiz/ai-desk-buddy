"""Tests for the Todoist API adapter."""

from datetime import date, datetime

import httpx
import pytest

from aideskbuddy.todoist import TodoistProviderError, TodoistRestProvider


def _task_payload(task_id: str = "task-1", content: str = "Buy milk") -> dict:
    return {
        "id": task_id,
        "content": content,
        "due": {
            "date": "2026-08-27",
            "string": "tomorrow",
            "is_recurring": False,
        },
    }


@pytest.mark.asyncio
async def test_create_list_and_complete_tasks() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["Authorization"] == "Bearer secret-token"
        if request.url.path == "/api/v1/tasks/filter":
            assert request.url.params["query"] == "today"
            assert request.url.params["limit"] == "5"
            return httpx.Response(200, json={"results": [_task_payload()]})
        if request.url.path == "/api/v1/tasks/task-1/close":
            return httpx.Response(200, json=None)
        assert request.url.path == "/api/v1/tasks"
        assert b'"due_date":"2026-08-27"' in request.content
        return httpx.Response(200, json=_task_payload())

    async with httpx.AsyncClient(
        base_url="https://api.todoist.com",
        transport=httpx.MockTransport(handler),
    ) as client:
        provider = TodoistRestProvider(token="secret-token", client=client)
        created = await provider.create_task(
            "Buy milk", due_date=date(2026, 8, 27)
        )
        tasks = await provider.list_tasks("today", limit=5)
        await provider.complete_task("task-1")

    assert created.content == "Buy milk"
    assert created.due_date == date(2026, 8, 27)
    assert tasks == [created]
    assert [request.method for request in requests] == ["POST", "GET", "POST"]


@pytest.mark.asyncio
async def test_create_task_sends_timezone_aware_due_datetime() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert b'"due_datetime":"2026-08-27T09:00:00+01:00"' in request.content
        return httpx.Response(200, json=_task_payload())

    async with httpx.AsyncClient(
        base_url="https://api.todoist.com",
        transport=httpx.MockTransport(handler),
    ) as client:
        provider = TodoistRestProvider(token="secret-token", client=client)
        await provider.create_task(
            "Submit expenses",
            due_at=datetime.fromisoformat("2026-08-27T09:00:00+01:00"),
        )


@pytest.mark.asyncio
async def test_todoist_authentication_failure_is_distinct() -> None:
    async with httpx.AsyncClient(
        base_url="https://api.todoist.com",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(401, json={"error": "unauthorized"})
        ),
    ) as client:
        provider = TodoistRestProvider(token="bad-token", client=client)
        with pytest.raises(TodoistProviderError, match="authentication failed"):
            await provider.list_tasks("today", limit=5)
