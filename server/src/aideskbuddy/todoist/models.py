"""Provider-neutral Todoist task models."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TodoistListPeriod = Literal["today", "overdue", "upcoming"]


class TodoistTask(BaseModel):
    """Task fields needed for concise Buddy interactions."""

    model_config = ConfigDict(frozen=True)

    id: str
    content: str = Field(min_length=1)
    due_date: date | None = None
    due_text: str | None = None
    is_recurring: bool = False
