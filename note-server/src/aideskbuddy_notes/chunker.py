"""Deterministic Markdown scanning and chunking."""

import hashlib
import re
import uuid
from pathlib import Path

from aideskbuddy_notes.models import NoteChunk

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_CHUNK_NAMESPACE = uuid.UUID("c3d88bd1-f2a8-4dc4-b435-c3fe9d98829e")


def scan_vault(
    vault_path: Path,
    *,
    owner_id: str,
    excluded_paths: tuple[str, ...],
    maximum_chunk_characters: int,
) -> list[NoteChunk]:
    """Read allowed Markdown files and produce deterministic, bounded chunks."""
    root = vault_path.resolve(strict=True)
    excluded = {item.strip("/") for item in excluded_paths if item.strip("/")}
    chunks: list[NoteChunk] = []
    for path in sorted(root.rglob("*.md")):
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root):
            continue
        relative = resolved.relative_to(root).as_posix()
        parts = set(Path(relative).parts)
        if any(item in parts or relative.startswith(f"{item}/") for item in excluded):
            continue
        text = resolved.read_text(encoding="utf-8")
        chunks.extend(
            chunk_markdown(
                text,
                relative_path=relative,
                owner_id=owner_id,
                maximum_characters=maximum_chunk_characters,
            )
        )
    return chunks


def chunk_markdown(
    text: str,
    *,
    relative_path: str,
    owner_id: str,
    maximum_characters: int,
) -> list[NoteChunk]:
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            sections.append((match.group(2).strip(), []))
        else:
            sections[-1][1].append(line)

    raw_chunks: list[tuple[str | None, str]] = []
    for heading, lines in sections:
        paragraphs = [item.strip() for item in _PARAGRAPH_BREAK.split("\n".join(lines))]
        paragraphs = [item for item in paragraphs if item]
        current = ""
        for paragraph in paragraphs:
            if current and len(current) + len(paragraph) + 2 > maximum_characters:
                raw_chunks.append((heading, current))
                current = ""
            if len(paragraph) > maximum_characters:
                if current:
                    raw_chunks.append((heading, current))
                    current = ""
                for start in range(0, len(paragraph), maximum_characters):
                    raw_chunks.append((heading, paragraph[start : start + maximum_characters]))
            else:
                current = f"{current}\n\n{paragraph}" if current else paragraph
        if current:
            raw_chunks.append((heading, current))

    chunks: list[NoteChunk] = []
    for number, (heading, content) in enumerate(raw_chunks):
        stable_key = f"{owner_id}\n{relative_path}\n{number}"
        chunks.append(
            NoteChunk(
                chunk_id=str(uuid.uuid5(_CHUNK_NAMESPACE, stable_key)),
                relative_path=relative_path,
                heading=heading,
                chunk_number=number,
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
                text=content,
            )
        )
    return chunks
