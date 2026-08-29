"""HTTP boundary tests for the standalone private notes service."""

from fastapi.testclient import TestClient

from aideskbuddy_notes.main import create_app
from aideskbuddy_notes.models import NoteAnswer


class FakeNotesService:
    chunk_count = 3
    last_error = None

    def __init__(self) -> None:
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    async def close(self) -> None:
        self.closed = True

    async def answer(self, question: str) -> NoteAnswer:
        assert question == "What display?"
        return NoteAnswer("Use SSD1306.", ("[[Hardware#Display]]",))

    async def reindex(self) -> int:
        return 2


def test_query_requires_token_and_returns_only_answer_and_citations() -> None:
    service = FakeNotesService()
    app = create_app(notes_service=service, service_token="secret")  # type: ignore[arg-type]

    with TestClient(app) as client:
        assert client.post("/v1/query", json={"question": "What display?"}).status_code == 401
        response = client.post(
            "/v1/query",
            headers={"Authorization": "Bearer secret"},
            json={"question": "What display?"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Use SSD1306.",
        "citations": ["[[Hardware#Display]]"],
    }
    assert service.started
    assert service.closed


def test_reindex_and_status_are_authenticated() -> None:
    service = FakeNotesService()
    app = create_app(notes_service=service, service_token="secret")  # type: ignore[arg-type]
    headers = {"Authorization": "Bearer secret"}

    with TestClient(app) as client:
        assert client.post("/v1/reindex", headers=headers).json() == {
            "changed_chunks": 2
        }
        assert client.get("/v1/index/status", headers=headers).json() == {
            "chunk_count": 3,
            "last_error": None,
        }
