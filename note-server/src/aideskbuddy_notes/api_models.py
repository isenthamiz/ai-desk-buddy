"""Private note-server HTTP models."""

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=1000)


class QueryResponse(BaseModel):
    answer: str
    citations: list[str]


class ReindexResponse(BaseModel):
    changed_chunks: int


class IndexStatusResponse(BaseModel):
    chunk_count: int
    last_error: str | None
