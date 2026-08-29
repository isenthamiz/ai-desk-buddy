"""Privacy-reduced Supabase pgvector adapter."""

from collections.abc import Sequence
from urllib.parse import urlparse

import httpx

from aideskbuddy_notes.models import NoteChunk, VectorMatch


class SupabaseVectorStore:
    """Store chunk metadata and embeddings without plaintext note content."""

    def __init__(
        self,
        *,
        base_url: str,
        service_role_key: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "https" and parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Supabase URL must use HTTPS unless it is local")
        if service_role_key.startswith("sb_publishable_"):
            raise ValueError(
                "Supabase note storage requires an sb_secret_ key, not a "
                "publishable key"
            )
        if not service_role_key.startswith(("sb_secret_", "eyJ")):
            raise ValueError(
                "Supabase note storage requires an sb_secret_ key or legacy "
                "service_role JWT"
            )
        self._base_url = base_url.rstrip("/")
        self._key = service_role_key
        self._uses_legacy_jwt = service_role_key.startswith("eyJ")
        self._client = client

    async def list_hashes(self, owner_id: str) -> dict[str, str]:
        response = await self._request(
            "GET",
            "/rest/v1/buddy_note_chunks",
            params={"select": "chunk_id,content_hash", "owner_id": f"eq.{owner_id}"},
        )
        try:
            return {
                str(item["chunk_id"]): str(item["content_hash"])
                for item in response.json()
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Supabase returned invalid note IDs") from exc

    async def list_embedding_ids(self, owner_id: str) -> set[str]:
        response = await self._request(
            "GET",
            "/rest/v1/buddy_note_embeddings",
            params={"select": "chunk_id", "owner_id": f"eq.{owner_id}"},
        )
        try:
            return {str(item["chunk_id"]) for item in response.json()}
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Supabase returned invalid embedding IDs") from exc

    async def upsert(
        self,
        owner_id: str,
        items: Sequence[tuple[NoteChunk, list[float]]],
    ) -> None:
        if not items:
            return
        await self._request(
            "POST",
            "/rest/v1/buddy_note_chunks",
            params={"on_conflict": "owner_id,chunk_id"},
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            json=[
                {
                    "owner_id": owner_id,
                    "chunk_id": chunk.chunk_id,
                    "relative_path": chunk.relative_path,
                    "heading": chunk.heading,
                    "chunk_number": chunk.chunk_number,
                    "content_hash": chunk.content_hash,
                }
                for chunk, _embedding in items
            ],
        )
        await self._request(
            "POST",
            "/rest/v1/buddy_note_embeddings",
            params={"on_conflict": "owner_id,chunk_id"},
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            json=[
                {
                    "owner_id": owner_id,
                    "chunk_id": chunk.chunk_id,
                    "content_hash": chunk.content_hash,
                    "embedding": embedding,
                }
                for chunk, embedding in items
            ],
        )

    async def delete(self, owner_id: str, chunk_ids: set[str]) -> None:
        for chunk_id in chunk_ids:
            await self._request(
                "DELETE",
                "/rest/v1/buddy_note_embeddings",
                params={
                    "owner_id": f"eq.{owner_id}",
                    "chunk_id": f"eq.{chunk_id}",
                },
            )
            await self._request(
                "DELETE",
                "/rest/v1/buddy_note_chunks",
                params={
                    "owner_id": f"eq.{owner_id}",
                    "chunk_id": f"eq.{chunk_id}",
                },
            )

    async def search(
        self,
        owner_id: str,
        embedding: list[float],
        *,
        limit: int,
        threshold: float,
    ) -> list[VectorMatch]:
        response = await self._request(
            "POST",
            "/rest/v1/rpc/match_buddy_note_embeddings",
            json={
                "match_owner_id": owner_id,
                "query_embedding": embedding,
                "match_count": limit,
                "match_threshold": threshold,
            },
        )
        try:
            return [
                VectorMatch(
                    chunk_id=str(item["chunk_id"]),
                    similarity=float(item["similarity"]),
                )
                for item in response.json()
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Supabase returned invalid vector matches") from exc

    async def _request(
        self, method: str, path: str, **kwargs: object
    ) -> httpx.Response:
        headers = {"apikey": self._key, **dict(kwargs.pop("headers", {}))}
        if self._uses_legacy_jwt:
            headers["Authorization"] = f"Bearer {self._key}"
        try:
            if self._client is not None:
                response = await self._client.request(
                    method, path, headers=headers, **kwargs
                )
            else:
                async with httpx.AsyncClient(
                    base_url=self._base_url, timeout=15.0
                ) as client:
                    response = await client.request(
                        method, path, headers=headers, **kwargs
                    )
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            raise RuntimeError("Supabase vector service unavailable") from exc
