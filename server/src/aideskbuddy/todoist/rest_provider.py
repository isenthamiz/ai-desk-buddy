"""Todoist API v1 HTTP adapter."""

from datetime import date, datetime
from typing import Any

import httpx

from aideskbuddy.todoist.models import TodoistListPeriod, TodoistTask
from aideskbuddy.todoist.provider import TodoistProviderError

_FILTERS: dict[TodoistListPeriod, str] = {
    "today": "today",
    "overdue": "overdue",
    "upcoming": "7 days",
}


class TodoistRestProvider:
    """Use Todoist's current REST-style API with a personal token."""

    def __init__(
        self, *, token: str, client: httpx.AsyncClient | None = None
    ) -> None:
        self._token = token
        self._client = client

    async def create_task(
        self,
        content: str,
        *,
        due_date: date | None = None,
        due_at: datetime | None = None,
    ) -> TodoistTask:
        payload: dict[str, object] = {"content": content}
        if due_date is not None:
            payload["due_date"] = due_date.isoformat()
        if due_at is not None:
            payload["due_datetime"] = due_at.isoformat()
        response = await self._request("POST", "/api/v1/tasks", json=payload)
        try:
            return self._parse_task(response.json())
        except (TypeError, ValueError) as exc:
            raise TodoistProviderError("Todoist returned invalid task data") from exc

    async def list_tasks(
        self, period: TodoistListPeriod, *, limit: int
    ) -> list[TodoistTask]:
        response = await self._request(
            "GET",
            "/api/v1/tasks/filter",
            params={"query": _FILTERS[period], "lang": "en", "limit": limit},
        )
        try:
            payload = response.json()
            return [self._parse_task(item) for item in payload["results"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise TodoistProviderError("Todoist returned invalid task data") from exc

    async def complete_task(self, task_id: str) -> None:
        await self._request("POST", f"/api/v1/tasks/{task_id}/close")

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            if self._client is not None:
                response = await self._client.request(
                    method, path, headers=headers, **kwargs
                )
            else:
                async with httpx.AsyncClient(
                    base_url="https://api.todoist.com", timeout=5.0
                ) as client:
                    response = await client.request(
                        method, path, headers=headers, **kwargs
                    )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                message = "Todoist authentication failed"
            elif status == 404:
                message = "Todoist task not found"
            else:
                message = "Todoist request failed"
            raise TodoistProviderError(message) from exc
        except httpx.HTTPError as exc:
            raise TodoistProviderError("Todoist service unavailable") from exc

    @staticmethod
    def _parse_task(payload: dict[str, Any]) -> TodoistTask:
        try:
            due = payload.get("due")
            due_date = None if due is None else date.fromisoformat(due["date"][:10])
            return TodoistTask(
                id=str(payload["id"]),
                content=str(payload["content"]),
                due_date=due_date,
                due_text=None if due is None else due.get("string"),
                is_recurring=False if due is None else bool(due.get("is_recurring")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TodoistProviderError("Todoist returned invalid task data") from exc
