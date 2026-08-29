"""Authenticated localhost client for private note queries."""

from urllib.parse import urlparse

import httpx


class NotesError(RuntimeError):
    """Raised when the private notes service cannot answer a request."""


class NotesClient:
    """Call the private notes process without exposing note chunks to this server."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {
            "localhost", "127.0.0.1", "::1"
        }:
            raise ValueError("private notes service URL must use HTTP on loopback")
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"), timeout=30
        )
        self._owns_client = client is None
        self._headers = {"Authorization": f"Bearer {token}"}

    async def answer(self, question: str) -> str:
        try:
            response = await self._client.post(
                "/v1/query", headers=self._headers, json={"question": question}
            )
            response.raise_for_status()
            payload = response.json()
            answer = str(payload["answer"])
            citations = [str(item) for item in payload.get("citations", [])]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise NotesError("private notes service request failed") from exc
        missing = [citation for citation in citations if citation not in answer]
        if missing:
            answer = f"{answer}\n\nSources: {', '.join(missing)}"
        return answer

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
