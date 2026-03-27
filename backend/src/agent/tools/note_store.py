from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
NOTES_DIR = DATA_DIR / "notes"
NOTES_META_DIR = DATA_DIR / "notes_meta"
NOTES_INDEX_PATH = DATA_DIR / "notes_index.json"


class SourceRef(BaseModel):
    type: str
    value: str


class NoteMetadata(BaseModel):
    note_id: str
    title: str
    filename: str
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    source_type: str = "text"
    source_ref: str = ""
    source_refs: list[SourceRef] = Field(default_factory=list)
    thread_id: Optional[str] = None
    status: str = "active"
    version: int = 1
    created_at: str
    updated_at: str
    last_modified_from: str = "create"
    rag_indexed: bool = False


class NoteRecord(BaseModel):
    metadata: NoteMetadata
    content: str


SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    NOTES_META_DIR.mkdir(parents=True, exist_ok=True)
    if not NOTES_INDEX_PATH.exists():
        NOTES_INDEX_PATH.write_text('{"notes": []}', encoding="utf-8")


def _sanitize_filename_stem(value: str) -> str:
    sanitized = SAFE_FILENAME_RE.sub("_", value.strip())
    sanitized = sanitized.strip("._")
    return sanitized or "note"


def _build_filename(note_id: str, title: str) -> str:
    stem = _sanitize_filename_stem(title)
    return f"{note_id}_{stem}.md"


def _meta_path(note_id: str) -> Path:
    return NOTES_META_DIR / f"{note_id}.json"


def _note_path(filename: str) -> Path:
    return NOTES_DIR / filename


def _load_index() -> dict[str, Any]:
    _ensure_dirs()
    try:
        return json.loads(NOTES_INDEX_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"notes": []}


def _save_index(index_data: dict[str, Any]) -> None:
    _ensure_dirs()
    NOTES_INDEX_PATH.write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _upsert_index(metadata: NoteMetadata) -> None:
    index_data = _load_index()
    notes = index_data.get("notes", [])
    summary_entry = {
        "note_id": metadata.note_id,
        "title": metadata.title,
        "filename": metadata.filename,
        "summary": metadata.summary,
        "updated_at": metadata.updated_at,
        "thread_id": metadata.thread_id,
        "version": metadata.version,
        "status": metadata.status,
        "source_type": metadata.source_type,
    }

    for idx, note in enumerate(notes):
        if note.get("note_id") == metadata.note_id:
            notes[idx] = summary_entry
            break
    else:
        notes.append(summary_entry)

    index_data["notes"] = sorted(
        notes,
        key=lambda item: item.get("updated_at", ""),
        reverse=True,
    )
    _save_index(index_data)


def list_notes(limit: int = 20) -> list[dict[str, Any]]:
    index_data = _load_index()
    notes = index_data.get("notes", [])
    return notes[: max(limit, 0)]


def create_note(
    title: str,
    content: str,
    *,
    summary: str = "",
    tags: Optional[list[str]] = None,
    source_type: str = "text",
    source_ref: str = "",
    source_refs: Optional[list[dict[str, str]]] = None,
    thread_id: Optional[str] = None,
) -> NoteMetadata:
    _ensure_dirs()

    note_id = f"note_{uuid4().hex[:12]}"
    filename = _build_filename(note_id, title)
    timestamp = _now_iso()

    metadata = NoteMetadata(
        note_id=note_id,
        title=title.strip() or "Untitled Note",
        filename=filename,
        summary=summary.strip(),
        tags=tags or [],
        source_type=source_type,
        source_ref=source_ref.strip(),
        source_refs=[SourceRef(**item) for item in (source_refs or [])],
        thread_id=thread_id,
        created_at=timestamp,
        updated_at=timestamp,
        last_modified_from="create",
    )

    _note_path(metadata.filename).write_text(content, encoding="utf-8")
    _meta_path(metadata.note_id).write_text(
        json.dumps(metadata.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _upsert_index(metadata)
    return metadata


def get_note(note_id: str) -> Optional[NoteRecord]:
    _ensure_dirs()
    meta_file = _meta_path(note_id)
    if not meta_file.exists():
        return None

    metadata = NoteMetadata.model_validate_json(meta_file.read_text(encoding="utf-8"))
    note_file = _note_path(metadata.filename)
    if not note_file.exists():
        return None

    return NoteRecord(metadata=metadata, content=note_file.read_text(encoding="utf-8"))


def update_note(
    note_id: str,
    *,
    content: str,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    tags: Optional[list[str]] = None,
    source_type: Optional[str] = None,
    source_ref: Optional[str] = None,
    thread_id: Optional[str] = None,
    last_modified_from: str = "edit",
) -> Optional[NoteMetadata]:
    record = get_note(note_id)
    if record is None:
        return None

    metadata = record.metadata
    old_note_path = _note_path(metadata.filename)

    if title is not None and title.strip():
        metadata.title = title.strip()
        metadata.filename = _build_filename(note_id, metadata.title)
    if summary is not None:
        metadata.summary = summary.strip()
    if tags is not None:
        metadata.tags = tags
    if source_type is not None and source_type.strip():
        metadata.source_type = source_type
    if source_ref is not None:
        metadata.source_ref = source_ref.strip()
    if thread_id is not None:
        metadata.thread_id = thread_id

    metadata.version += 1
    metadata.updated_at = _now_iso()
    metadata.last_modified_from = last_modified_from
    metadata.rag_indexed = False

    new_note_path = _note_path(metadata.filename)
    if old_note_path != new_note_path and old_note_path.exists():
        old_note_path.unlink()

    new_note_path.write_text(content, encoding="utf-8")
    _meta_path(note_id).write_text(
        json.dumps(metadata.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _upsert_index(metadata)
    return metadata

