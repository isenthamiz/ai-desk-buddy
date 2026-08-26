"""Todoist application service."""

from datetime import date, datetime

from aideskbuddy.todoist.models import TodoistListPeriod, TodoistTask
from aideskbuddy.todoist.provider import TodoistProvider


class TodoistService:
    def __init__(self, provider: TodoistProvider) -> None:
        self._provider = provider

    async def create_task(
        self,
        content: str,
        *,
        due_date: date | None = None,
        due_at: datetime | None = None,
    ) -> TodoistTask:
        return await self._provider.create_task(
            content, due_date=due_date, due_at=due_at
        )

    async def list_tasks(
        self, period: TodoistListPeriod, *, limit: int = 5
    ) -> list[TodoistTask]:
        return await self._provider.list_tasks(period, limit=limit)

    async def complete_task(self, task_id: str) -> None:
        await self._provider.complete_task(task_id)
