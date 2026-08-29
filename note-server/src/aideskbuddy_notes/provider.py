"""Boundaries for model inference and remote vector storage."""

from typing import Protocol, Sequence

from aideskbuddy_notes.models import NoteChunk, VectorMatch


class NotesModelProvider(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings for note text or a query."""

    async def answer(
        self, question: str, passages: Sequence[tuple[str, str]]
    ) -> str:
        """Answer from selected passages using the configured model."""


class NotesVectorStore(Protocol):
    async def list_hashes(self, owner_id: str) -> dict[str, str]:
        """Map remote opaque chunk IDs to content hashes for reconciliation."""

    async def list_embedding_ids(self, owner_id: str) -> set[str]:
        """List remotely embedded chunk IDs for migration-safe reconciliation."""

    async def upsert(
        self,
        owner_id: str,
        items: Sequence[tuple[NoteChunk, list[float]]],
    ) -> None:
        """Store chunk metadata and embeddings without note text."""

    async def delete(self, owner_id: str, chunk_ids: set[str]) -> None:
        """Delete stale opaque chunk IDs."""

    async def search(
        self,
        owner_id: str,
        embedding: list[float],
        *,
        limit: int,
        threshold: float,
    ) -> list[VectorMatch]:
        """Return nearest opaque chunk IDs."""
