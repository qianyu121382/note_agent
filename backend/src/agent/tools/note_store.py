from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from psycopg import connect
from pydantic import BaseModel, Field

from agent.utils.logging import logger

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
LEGACY_NOTES_DIR = DATA_DIR / "notes"
LEGACY_NOTES_META_DIR = DATA_DIR / "notes_meta"
TABLE_NAME = "notes"

SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
TOKEN_RE = re.compile(r"[A-Za-z0-9_\-\u4e00-\u9fff]+")


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


class NoteConflictError(Exception):
    def __init__(self, note_id: str, expected_version: int, actual_version: int):
        self.note_id = note_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Conflict updating note '{note_id}': expected version {expected_version}, actual version {actual_version}."
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_postgres_uri() -> str:
    value = os.getenv("POSTGRES_URI")
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise RuntimeError("POSTGRES_URI is required for note storage.")


def _connect(*, autocommit: bool = True):
    return connect(_get_postgres_uri(), autocommit=autocommit)


def _ensure_table() -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    note_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    filename TEXT NOT NULL UNIQUE,
                    content TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                    source_type TEXT NOT NULL DEFAULT 'text',
                    source_ref TEXT NOT NULL DEFAULT '',
                    source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
                    thread_id TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    version INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    last_modified_from TEXT NOT NULL DEFAULT 'create',
                    rag_indexed BOOLEAN NOT NULL DEFAULT FALSE
                )
                """
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_updated_at ON {TABLE_NAME} (updated_at DESC)"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_thread_id ON {TABLE_NAME} (thread_id)"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_title ON {TABLE_NAME} (title)"
            )


def _sanitize_filename_stem(value: str) -> str:
    sanitized = SAFE_FILENAME_RE.sub("_", value.strip())
    sanitized = sanitized.strip("._")
    return sanitized or "note"


def _build_filename(note_id: str, title: str) -> str:
    stem = _sanitize_filename_stem(title)
    return f"{note_id}_{stem}.md"


def _serialize_source_refs(source_refs: list[SourceRef]) -> str:
    return json.dumps([item.model_dump() for item in source_refs], ensure_ascii=False)


def _row_to_metadata(row: dict[str, Any]) -> NoteMetadata:
    return NoteMetadata(
        note_id=row["note_id"],
        title=row["title"],
        filename=row["filename"],
        summary=row.get("summary") or "",
        tags=list(row.get("tags") or []),
        source_type=row.get("source_type") or "text",
        source_ref=row.get("source_ref") or "",
        source_refs=[SourceRef(**item) for item in (row.get("source_refs") or [])],
        thread_id=row.get("thread_id"),
        status=row.get("status") or "active",
        version=int(row.get("version") or 1),
        created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
        updated_at=row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"]),
        last_modified_from=row.get("last_modified_from") or "create",
        rag_indexed=bool(row.get("rag_indexed")),
    )


def _summary_row_from_metadata(metadata: NoteMetadata) -> dict[str, Any]:
    return {
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


def _set_rag_indexed(note_id: str, rag_indexed: bool) -> None:
    _ensure_table()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {TABLE_NAME} SET rag_indexed = %s, updated_at = updated_at WHERE note_id = %s",
                (rag_indexed, note_id),
            )


def set_note_rag_indexed(note_id: str, rag_indexed: bool) -> None:
    _set_rag_indexed(note_id, rag_indexed)


def list_notes(limit: int = 20) -> list[dict[str, Any]]:
    _ensure_table()
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT note_id, title, filename, summary, updated_at, thread_id, version, status, source_type
                FROM {TABLE_NAME}
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (max(limit, 0),),
            )
            rows = cur.fetchall()
    summaries = []
    for row in rows:
        item = dict(row)
        updated = item.get("updated_at")
        if hasattr(updated, "isoformat"):
            item["updated_at"] = updated.isoformat()
        summaries.append(item)
    return summaries


def _tokenize_query(value: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(value)]


def search_notes(query: str, limit: int = 5) -> list[dict[str, Any]]:
    notes = list_notes(limit=200)
    cleaned_query = query.strip()
    if not cleaned_query:
        return notes[: max(limit, 0)]

    query_lower = cleaned_query.lower()
    query_tokens = _tokenize_query(cleaned_query)
    scored: list[tuple[int, dict[str, Any]]] = []

    for note in notes:
        title = str(note.get("title", ""))
        summary = str(note.get("summary", ""))
        note_id = str(note.get("note_id", ""))
        filename = str(note.get("filename", ""))
        haystack = " ".join([title, summary, note_id, filename]).lower()

        score = 0
        if note_id.lower() == query_lower:
            score += 100
        if query_lower in title.lower():
            score += 40
        if query_lower in summary.lower():
            score += 20
        if query_lower in haystack:
            score += 10

        for token in query_tokens:
            if token == note_id.lower():
                score += 25
            if token in title.lower():
                score += 12
            if token in summary.lower():
                score += 6
            if token in haystack:
                score += 3

        if score > 0:
            scored.append((score, note))

    scored.sort(
        key=lambda item: (item[0], item[1].get("updated_at", "")),
        reverse=True,
    )
    return [note for _, note in scored[: max(limit, 0)]]


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
    _ensure_table()

    note_id = f"note_{uuid4().hex[:12]}"
    filename = _build_filename(note_id, title)
    timestamp = datetime.now(timezone.utc)
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
        created_at=timestamp.isoformat(),
        updated_at=timestamp.isoformat(),
        last_modified_from="create",
    )

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    note_id, title, filename, content, summary, tags, source_type,
                    source_ref, source_refs, thread_id, status, version,
                    created_at, updated_at, last_modified_from, rag_indexed
                )
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    metadata.note_id,
                    metadata.title,
                    metadata.filename,
                    content,
                    metadata.summary,
                    json.dumps(metadata.tags, ensure_ascii=False),
                    metadata.source_type,
                    metadata.source_ref,
                    _serialize_source_refs(metadata.source_refs),
                    metadata.thread_id,
                    metadata.status,
                    metadata.version,
                    metadata.created_at,
                    metadata.updated_at,
                    metadata.last_modified_from,
                    metadata.rag_indexed,
                ),
            )

    return metadata


def get_note(note_id: str) -> Optional[NoteRecord]:
    _ensure_table()
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(f"SELECT * FROM {TABLE_NAME} WHERE note_id = %s LIMIT 1", (note_id,))
            row = cur.fetchone()
    if row is None:
        return None
    metadata = _row_to_metadata(dict(row))
    return NoteRecord(metadata=metadata, content=row["content"])


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
    expected_version: Optional[int] = None,
) -> Optional[NoteMetadata]:
    _ensure_table()
    with _connect(autocommit=False) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(f"SELECT * FROM {TABLE_NAME} WHERE note_id = %s FOR UPDATE", (note_id,))
            row = cur.fetchone()
            if row is None:
                conn.rollback()
                return None

            metadata = _row_to_metadata(dict(row))
            if expected_version is not None and metadata.version != expected_version:
                conn.rollback()
                raise NoteConflictError(
                    note_id=note_id,
                    expected_version=expected_version,
                    actual_version=metadata.version,
                )

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

            cur.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET title = %s,
                    filename = %s,
                    content = %s,
                    summary = %s,
                    tags = %s::jsonb,
                    source_type = %s,
                    source_ref = %s,
                    thread_id = %s,
                    version = %s,
                    updated_at = %s,
                    last_modified_from = %s,
                    rag_indexed = %s
                WHERE note_id = %s
                """,
                (
                    metadata.title,
                    metadata.filename,
                    content,
                    metadata.summary,
                    json.dumps(metadata.tags, ensure_ascii=False),
                    metadata.source_type,
                    metadata.source_ref,
                    metadata.thread_id,
                    metadata.version,
                    metadata.updated_at,
                    metadata.last_modified_from,
                    metadata.rag_indexed,
                    note_id,
                ),
            )
        conn.commit()

    return metadata


def delete_note(note_id: str) -> Optional[NoteMetadata]:
    _ensure_table()
    with _connect(autocommit=False) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(f"SELECT * FROM {TABLE_NAME} WHERE note_id = %s FOR UPDATE", (note_id,))
            row = cur.fetchone()
            if row is None:
                conn.rollback()
                return None

            metadata = _row_to_metadata(dict(row))
            cur.execute(f"DELETE FROM {TABLE_NAME} WHERE note_id = %s", (note_id,))
        conn.commit()
    return metadata


def note_filename_exists(filename: str) -> bool:
    _ensure_table()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT 1 FROM {TABLE_NAME} WHERE filename = %s LIMIT 1", (filename,))
            return cur.fetchone() is not None


def import_legacy_notes_from_disk() -> int:
    _ensure_table()
    imported = 0
    if not LEGACY_NOTES_META_DIR.exists():
        return imported

    with _connect() as conn:
        with conn.cursor() as cur:
            for meta_path in sorted(LEGACY_NOTES_META_DIR.glob("*.json")):
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
                note_id = payload.get("note_id")
                if not note_id:
                    continue
                filename = payload.get("filename") or _build_filename(note_id, payload.get("title", "Untitled Note"))
                content_path = LEGACY_NOTES_DIR / filename
                if not content_path.exists():
                    continue
                content = content_path.read_text(encoding="utf-8")
                source_refs = payload.get("source_refs") or []
                tags = payload.get("tags") or []
                cur.execute(
                    f"""
                    INSERT INTO {TABLE_NAME} (
                        note_id, title, filename, content, summary, tags, source_type,
                        source_ref, source_refs, thread_id, status, version,
                        created_at, updated_at, last_modified_from, rag_indexed
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (note_id) DO NOTHING
                    """,
                    (
                        note_id,
                        payload.get("title") or "Untitled Note",
                        filename,
                        content,
                        payload.get("summary") or "",
                        json.dumps(tags, ensure_ascii=False),
                        payload.get("source_type") or "text",
                        payload.get("source_ref") or "",
                        json.dumps(source_refs, ensure_ascii=False),
                        payload.get("thread_id"),
                        payload.get("status") or "active",
                        int(payload.get("version") or 1),
                        payload.get("created_at") or _now_iso(),
                        payload.get("updated_at") or _now_iso(),
                        payload.get("last_modified_from") or "create",
                        bool(payload.get("rag_indexed")),
                    ),
                )
                imported += cur.rowcount
    return imported


from psycopg.rows import dict_row

__all__ = [
    "SourceRef",
    "NoteMetadata",
    "NoteRecord",
    "NoteConflictError",
    "create_note",
    "get_note",
    "update_note",
    "delete_note",
    "list_notes",
    "search_notes",
    "set_note_rag_indexed",
    "note_filename_exists",
    "import_legacy_notes_from_disk",
]
