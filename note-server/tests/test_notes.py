"""Tests for private Obsidian RAG indexing and retrieval."""

from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from aideskbuddy_notes import (
    NotesRagService,
    OpenAINotesProvider,
    SupabaseVectorStore,
    VectorMatch,
)
from aideskbuddy_notes.chunker import scan_vault


class FakeLocalProvider:
    def __init__(self) -> None:
        self.answered_with: list[tuple[str, str]] = []

    async def embed(self, texts):
        return [[float(len(text)), 1.0] for text in texts]

    async def answer(self, question, passages):
        assert question == "What did I decide about the display?"
        self.answered_with = list(passages)
        return f"Use the SSD1306. {passages[0][0]}"


class FakeVectorStore:
    def __init__(self) -> None:
        self.items: dict[str, tuple[str, list[float]]] = {}

    async def list_hashes(self, _owner_id):
        return {chunk_id: item[0] for chunk_id, item in self.items.items()}

    async def list_embedding_ids(self, _owner_id):
        return set(self.items)

    async def upsert(self, _owner_id, items):
        for chunk, embedding in items:
            self.items[chunk.chunk_id] = (chunk.content_hash, embedding)

    async def delete(self, _owner_id, chunk_ids):
        for chunk_id in chunk_ids:
            self.items.pop(chunk_id, None)

    async def search(self, _owner_id, _embedding, *, limit, threshold):
        del limit, threshold
        return [VectorMatch(chunk_id=chunk_id, similarity=0.9) for chunk_id in self.items]


@pytest.mark.asyncio
async def test_notes_index_stores_no_note_text_and_answers_from_selected_chunk(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Desk Buddy.md").write_text(
        "# Display decision\n\nUse the SSD1306 for the first hardware version.",
        encoding="utf-8",
    )
    local = FakeLocalProvider()
    vectors = FakeVectorStore()
    service = NotesRagService(
        vault_path=vault,
        owner_id="owner-1",
        excluded_paths=(".obsidian",),
        local_provider=local,
        vector_store=vectors,
    )

    assert await service.reindex() == 1
    answer = await service.answer("What did I decide about the display?")

    assert answer.answer == "Use the SSD1306. [[Desk Buddy#Display decision]]"
    assert answer.citations == ("[[Desk Buddy#Display decision]]",)
    assert local.answered_with == [
        (
            "[[Desk Buddy#Display decision]]",
            "Use the SSD1306 for the first hardware version.",
        )
    ]
    assert all(len(item) == 2 for item in vectors.items.values())


@pytest.mark.asyncio
async def test_reindex_updates_changed_chunks_and_deletes_removed_chunks(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "Note.md"
    note.write_text("First version", encoding="utf-8")
    vectors = FakeVectorStore()
    service = NotesRagService(
        vault_path=vault,
        owner_id="owner-1",
        excluded_paths=(),
        local_provider=FakeLocalProvider(),
        vector_store=vectors,
    )
    await service.reindex()
    assert len(vectors.items) == 1

    note.write_text("Second version", encoding="utf-8")
    assert await service.reindex() == 1
    assert len(vectors.items) == 1

    note.unlink()
    assert await service.reindex() == 0
    assert vectors.items == {}


def test_vault_scan_excludes_private_paths_and_outside_symlinks(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    private = vault / "Private"
    private.mkdir(parents=True)
    (vault / "Visible.md").write_text("Visible information", encoding="utf-8")
    (private / "Secret.md").write_text("Secret information", encoding="utf-8")
    outside = tmp_path / "Outside.md"
    outside.write_text("Outside information", encoding="utf-8")
    (vault / "Link.md").symlink_to(outside)

    chunks = scan_vault(
        vault,
        owner_id="owner-1",
        excluded_paths=("Private",),
        maximum_chunk_characters=1600,
    )

    assert [chunk.text for chunk in chunks] == ["Visible information"]


@pytest.mark.asyncio
async def test_supabase_payload_never_contains_note_text_or_location() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json=None)

    async with httpx.AsyncClient(
        base_url="https://example.supabase.co",
        transport=httpx.MockTransport(handler),
    ) as client:
        store = SupabaseVectorStore(
            base_url="https://example.supabase.co",
            service_role_key="sb_secret_test",
            client=client,
        )
        chunk = scan_vault_chunk()
        await store.upsert("owner-1", [(chunk, [0.1, 0.2])])

    metadata_body = requests[0].content.decode()
    embedding_body = requests[1].content.decode()
    assert "Private note contents" not in metadata_body
    assert "Notes/Private.md" in metadata_body
    assert "Private heading" in metadata_body
    assert '"chunk_number":0' in metadata_body
    assert '"content_hash"' in metadata_body
    assert "Private note contents" not in embedding_body
    assert "Notes/Private.md" not in embedding_body
    assert '"embedding"' in embedding_body
    assert requests[0].headers["apikey"] == "sb_secret_test"
    assert "Authorization" not in requests[0].headers


def test_supabase_rejects_publishable_key() -> None:
    with pytest.raises(ValueError, match="not a publishable key"):
        SupabaseVectorStore(
            base_url="https://example.supabase.co",
            service_role_key="sb_publishable_test",
        )


def scan_vault_chunk():
    from aideskbuddy_notes import NoteChunk

    return NoteChunk(
        chunk_id="c926a3f1-72e3-4c9a-851c-f240184f9aaf",
        relative_path="Notes/Private.md",
        heading="Private heading",
        chunk_number=0,
        content_hash="hash",
        text="Private note contents",
    )


def test_supabase_migration_qualifies_vector_operator() -> None:
    migration = (
        Path(__file__).parents[1] / "supabase" / "notes.sql"
    ).read_text(encoding="utf-8")

    assert migration.count("OPERATOR(extensions.<=>)") == 3
    assert "embedding <=>" not in migration
    assert "ON public.buddy_note_embeddings TO service_role" in migration
    assert "ON public.buddy_note_chunks TO service_role" in migration


@pytest.mark.asyncio
async def test_openai_provider_embeds_and_answers_from_selected_passages() -> None:
    calls: dict[str, dict[str, object]] = {}

    class Embeddings:
        async def create(self, **kwargs):
            calls["embeddings"] = kwargs
            return SimpleNamespace(
                data=[SimpleNamespace(index=0, embedding=[0.1, 0.2])]
            )

    class Responses:
        async def create(self, **kwargs):
            calls["responses"] = kwargs
            return SimpleNamespace(
                output_text="Use the SSD1306. [[Desk Buddy#Display]]"
            )

    provider = OpenAINotesProvider(
        api_key="test-key",
        embedding_model="text-embedding-3-small",
        chat_model="gpt-5-mini",
        embedding_dimensions=768,
        client=SimpleNamespace(
            embeddings=Embeddings(),
            responses=Responses(),
        )
    )
    assert await provider.embed(["display decision"]) == [[0.1, 0.2]]
    answer = await provider.answer(
        "What display?",
        [("[[Desk Buddy#Display]]", "Use the SSD1306")],
    )

    assert answer == "Use the SSD1306. [[Desk Buddy#Display]]"
    assert calls["embeddings"]["dimensions"] == 768
    assert "Use the SSD1306" in str(calls["responses"]["input"])
    assert calls["responses"]["reasoning"] == {"effort": "minimal"}
    assert calls["responses"]["max_output_tokens"] == 1200
    assert calls["responses"]["store"] is False
