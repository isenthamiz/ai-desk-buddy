"""Provider-neutral Todoist boundary."""

from datetime import date, datetime
from typing import Protocol

from aideskbuddy.todoist.models import TodoistListPeriod, TodoistTask


class TodoistProviderError(RuntimeError):
    """Raised when Todoist rejects or cannot complete an operation."""


class TodoistProvider(Protocol):
    async def create_task(
        self,
        content: str,
        *,
        due_date: date | None = None,
        due_at: datetime | None = None,
    ) -> TodoistTask:
        """Create an Inbox task."""

    async def list_tasks(
        self, period: TodoistListPeriod, *, limit: int
    ) -> list[TodoistTask]:
        """List active tasks for a supported period."""

    async def complete_task(self, task_id: str) -> None:
        """Complete an active task by exact ID."""
