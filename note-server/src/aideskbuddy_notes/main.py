"""Standalone private notes FastAPI service."""

import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status

from aideskbuddy_notes.api_models import (
    IndexStatusResponse,
    QueryRequest,
    QueryResponse,
    ReindexResponse,
)
from aideskbuddy_notes.openai_provider import OpenAINotesProvider
from aideskbuddy_notes.service import NotesError, NotesRagService
from aideskbuddy_notes.supabase import SupabaseVectorStore

NOTE_SERVER_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(NOTE_SERVER_ROOT / ".env")


def _required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _supabase_server_key() -> str:
    value = os.getenv("NOTES_SUPABASE_SECRET_KEY") or os.getenv(
        "NOTES_SUPABASE_SERVICE_ROLE_KEY"
    )
    if not value:
        raise ValueError(
            "NOTES_SUPABASE_SECRET_KEY is required (a legacy "
            "NOTES_SUPABASE_SERVICE_ROLE_KEY is also accepted)"
        )
    return value


def _service_from_environment() -> NotesRagService:
    vault_path = Path(_required_environment("OBSIDIAN_VAULT_PATH")).resolve()
    if not vault_path.is_dir():
        raise ValueError("OBSIDIAN_VAULT_PATH must be an existing directory")
    excluded = tuple(
        item.strip()
        for item in os.getenv(
            "NOTES_EXCLUDE_PATHS", ".obsidian,.trash,Private"
        ).split(",")
        if item.strip()
    )
    return NotesRagService(
        vault_path=vault_path,
        owner_id=_required_environment("NOTES_OWNER_ID"),
        excluded_paths=excluded,
        local_provider=OpenAINotesProvider(
            api_key=_required_environment("OPENAI_API_KEY"),
            embedding_model=os.getenv(
                "NOTES_EMBEDDING_MODEL", "text-embedding-3-small"
            ),
            chat_model=os.getenv("NOTES_CHAT_MODEL", "gpt-5-mini"),
            embedding_dimensions=768,
        ),
        vector_store=SupabaseVectorStore(
            base_url=_required_environment("NOTES_SUPABASE_URL"),
            service_role_key=_supabase_server_key(),
        ),
        reconcile_seconds=float(os.getenv("NOTES_RECONCILE_SECONDS", "60")),
    )


def create_app(
    *,
    notes_service: NotesRagService | None = None,
    service_token: str | None = None,
) -> FastAPI:
    configured_token = service_token or os.getenv("NOTES_SERVICE_TOKEN")

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        if not configured_token:
            raise ValueError("NOTES_SERVICE_TOKEN is required")
        service = notes_service or _service_from_environment()
        application.state.notes = service
        service.start()
        try:
            yield
        finally:
            await service.close()

    application = FastAPI(title="AI Desk Buddy Private Notes", lifespan=lifespan)

    def authorize(authorization: str | None = Header(default=None)) -> None:
        expected = f"Bearer {configured_token}"
        if authorization is None or not secrets.compare_digest(authorization, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid notes service token",
            )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post(
        "/v1/query", response_model=QueryResponse, dependencies=[Depends(authorize)]
    )
    async def query(request: QueryRequest) -> QueryResponse:
        try:
            result = await application.state.notes.answer(request.question)
        except NotesError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return QueryResponse(answer=result.answer, citations=list(result.citations))

    @application.post(
        "/v1/reindex",
        response_model=ReindexResponse,
        dependencies=[Depends(authorize)],
    )
    async def reindex() -> ReindexResponse:
        try:
            changed = await application.state.notes.reindex()
        except NotesError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return ReindexResponse(changed_chunks=changed)

    @application.get(
        "/v1/index/status",
        response_model=IndexStatusResponse,
        dependencies=[Depends(authorize)],
    )
    async def index_status() -> IndexStatusResponse:
        service = application.state.notes
        return IndexStatusResponse(
            chunk_count=service.chunk_count,
            last_error=service.last_error,
        )

    return application


app = create_app()
