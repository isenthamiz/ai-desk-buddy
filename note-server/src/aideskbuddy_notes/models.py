"""Private notes domain models."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NoteChunk:
    chunk_id: str
    relative_path: str
    heading: str | None
    chunk_number: int
    content_hash: str
    text: str

    @property
    def citation(self) -> str:
        note = self.relative_path.removesuffix(".md")
        suffix = f"#{self.heading}" if self.heading else ""
        return f"[[{note}{suffix}]]"


@dataclass(frozen=True, slots=True)
class VectorMatch:
    chunk_id: str
    similarity: float


@dataclass(frozen=True, slots=True)
class NoteAnswer:
    answer: str
    citations: tuple[str, ...]
