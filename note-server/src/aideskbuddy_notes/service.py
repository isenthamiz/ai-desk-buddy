"""Private hybrid retrieval and local answer orchestration."""

import asyncio
import logging
import re
from pathlib import Path

from aideskbuddy_notes.chunker import scan_vault
from aideskbuddy_notes.models import NoteAnswer, NoteChunk
from aideskbuddy_notes.provider import NotesModelProvider, NotesVectorStore

LOGGER = logging.getLogger(__name__)
_TERMS = re.compile(r"[\w'-]+", re.UNICODE)


class NotesError(RuntimeError):
    """Raised when private note retrieval cannot produce an answer."""


class NotesRagService:
    def __init__(
        self,
        *,
        vault_path: Path,
        owner_id: str,
        excluded_paths: tuple[str, ...],
        local_provider: NotesModelProvider,
        vector_store: NotesVectorStore,
        maximum_chunk_characters: int = 1600,
        result_limit: int = 4,
        vector_threshold: float = 0.25,
        reconcile_seconds: float = 60.0,
    ) -> None:
        self._vault_path = vault_path
        self._owner_id = owner_id
        self._excluded_paths = excluded_paths
        self._local = local_provider
        self._vectors = vector_store
        self._maximum_chunk_characters = maximum_chunk_characters
        self._result_limit = result_limit
        self._vector_threshold = vector_threshold
        self._reconcile_seconds = reconcile_seconds
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._chunk_count = 0
        self._last_error: str | None = None

    @property
    def chunk_count(self) -> int:
        return self._chunk_count

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._reconcile_loop())

    async def close(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def reindex(self) -> int:
        async with self._lock:
            try:
                chunks = await asyncio.to_thread(self._scan)
                remote_hashes = await self._vectors.list_hashes(self._owner_id)
                remote_embedding_ids = await self._vectors.list_embedding_ids(
                    self._owner_id
                )
                changed = [
                    chunk
                    for chunk in chunks
                    if remote_hashes.get(chunk.chunk_id) != chunk.content_hash
                    or chunk.chunk_id not in remote_embedding_ids
                ]
                for start in range(0, len(changed), 16):
                    batch = changed[start : start + 16]
                    embeddings = await self._local.embed([item.text for item in batch])
                    await self._vectors.upsert(
                        self._owner_id, list(zip(batch, embeddings, strict=True))
                    )
                current_ids = {item.chunk_id for item in chunks}
                await self._vectors.delete(
                    self._owner_id,
                    (set(remote_hashes) | remote_embedding_ids) - current_ids,
                )
                self._chunk_count = len(chunks)
                self._last_error = None
                return len(changed)
            except (OSError, RuntimeError, ValueError) as exc:
                self._last_error = str(exc)
                raise NotesError(str(exc)) from exc

    async def answer(self, question: str) -> NoteAnswer:
        question = question.strip()
        if not question:
            raise NotesError("Ask a question after 'notes:'.")
        try:
            chunks = await asyncio.to_thread(self._scan)
            by_id = {item.chunk_id: item for item in chunks}
            query_embedding = (await self._local.embed([question]))[0]
            vector_matches = await self._vectors.search(
                self._owner_id,
                query_embedding,
                limit=max(10, self._result_limit * 2),
                threshold=self._vector_threshold,
            )
            keyword_ids = self._keyword_rank(question, chunks)
            ranked_ids = self._combine_rankings(
                [item.chunk_id for item in vector_matches], keyword_ids
            )
            selected = [by_id[item] for item in ranked_ids if item in by_id][
                : self._result_limit
            ]
            if not selected:
                return NoteAnswer(
                    answer="I couldn't find that in your notes.", citations=()
                )
            answer = await self._local.answer(
                question, [(item.citation, item.text) for item in selected]
            )
            return NoteAnswer(
                answer=answer,
                citations=tuple(item.citation for item in selected),
            )
        except (OSError, RuntimeError, ValueError) as exc:
            raise NotesError(str(exc)) from exc

    def _scan(self) -> list[NoteChunk]:
        return scan_vault(
            self._vault_path,
            owner_id=self._owner_id,
            excluded_paths=self._excluded_paths,
            maximum_chunk_characters=self._maximum_chunk_characters,
        )

    @staticmethod
    def _keyword_rank(question: str, chunks: list[NoteChunk]) -> list[str]:
        terms = {term.lower() for term in _TERMS.findall(question) if len(term) > 2}
        scored: list[tuple[int, str]] = []
        for chunk in chunks:
            haystack = f"{chunk.relative_path} {chunk.heading or ''} {chunk.text}".lower()
            score = sum(haystack.count(term) for term in terms)
            if score:
                scored.append((score, chunk.chunk_id))
        return [item[1] for item in sorted(scored, reverse=True)]

    @staticmethod
    def _combine_rankings(vector_ids: list[str], keyword_ids: list[str]) -> list[str]:
        scores: dict[str, float] = {}
        for ranking in (vector_ids, keyword_ids):
            for rank, chunk_id in enumerate(ranking, start=1):
                scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (60 + rank)
        return sorted(scores, key=scores.get, reverse=True)  # type: ignore[arg-type]

    async def _reconcile_loop(self) -> None:
        while True:
            try:
                await self.reindex()
            except NotesError:
                LOGGER.exception("Private note index reconciliation failed")
            await asyncio.sleep(self._reconcile_seconds)
