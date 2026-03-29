from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import NAMESPACE_URL, uuid4, uuid5

from langchain_openai import OpenAIEmbeddings
from psycopg import connect
from qdrant_client import QdrantClient, models

from agent.utils.logging import logger

PROJECT_ROOT = Path(__file__).resolve().parents[3]
QDRANT_DEFAULT_PATH = PROJECT_ROOT / "data" / "qdrant"
CHUNKS_TABLE_NAME = "note_chunks"
QDRANT_COLLECTION_NAME = "note_chunks"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
MAX_CHUNK_CHARS = 1200
MIN_CHUNK_CHARS = 300

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class NoteChunk:
    chunk_id: str
    note_id: str
    chunk_index: int
    section_title: str
    content: str
    char_count: int
    source_ref: str


@dataclass
class RetrievedChunk:
    chunk_id: str
    note_id: str
    chunk_index: int
    section_title: str
    content: str
    char_count: int
    source_ref: str
    score: float


def _get_postgres_uri() -> str:
    value = os.getenv("POSTGRES_URI")
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise RuntimeError("POSTGRES_URI is required for RAG chunk storage.")


def _connect(*, autocommit: bool = True):
    return connect(_get_postgres_uri(), autocommit=autocommit)


def _get_qdrant_path() -> str:
    value = os.getenv("QDRANT_PATH")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return str(QDRANT_DEFAULT_PATH)


def _get_qdrant_collection() -> str:
    value = os.getenv("QDRANT_COLLECTION")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return QDRANT_COLLECTION_NAME


def _get_embedding_model() -> str:
    value = os.getenv("EMBEDDING_MODEL")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_EMBEDDING_MODEL


def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=_get_embedding_model())


def _get_qdrant_client() -> QdrantClient:
    return QdrantClient(path=_get_qdrant_path())


def ensure_note_chunks_table() -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {CHUNKS_TABLE_NAME} (
                    chunk_id TEXT PRIMARY KEY,
                    note_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    section_title TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    char_count INTEGER NOT NULL,
                    source_ref TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_{CHUNKS_TABLE_NAME}_note_chunk
                ON {CHUNKS_TABLE_NAME} (note_id, chunk_index)
                """
            )
            cur.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{CHUNKS_TABLE_NAME}_note_id
                ON {CHUNKS_TABLE_NAME} (note_id)
                """
            )


def ensure_qdrant_collection(vector_size: int) -> None:
    client = _get_qdrant_client()
    collection_name = _get_qdrant_collection()
    if client.collection_exists(collection_name):
        return
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
        ),
    )


def _normalize_whitespace(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.strip().splitlines()).strip()


def _finalize_chunk(
    chunks: list[NoteChunk],
    *,
    note_id: str,
    chunk_index: int,
    section_title: str,
    content: str,
    source_ref: str,
) -> int:
    normalized = _normalize_whitespace(content)
    if not normalized:
        return chunk_index
    chunks.append(
        NoteChunk(
            chunk_id=f"{note_id}_chunk_{chunk_index:04d}_{uuid4().hex[:8]}",
            note_id=note_id,
            chunk_index=chunk_index,
            section_title=section_title or "Untitled Section",
            content=normalized,
            char_count=len(normalized),
            source_ref=source_ref,
        )
    )
    return chunk_index + 1


def split_markdown_into_chunks(
    *,
    note_id: str,
    title: str,
    content: str,
    source_ref: str = "",
) -> list[NoteChunk]:
    lines = content.splitlines()
    current_section = title.strip() or "Untitled Note"
    current_buffer: list[str] = []
    chunks: list[NoteChunk] = []
    chunk_index = 0

    def flush_buffer() -> None:
        nonlocal chunk_index, current_buffer
        if not current_buffer:
            return
        text = "\n".join(current_buffer).strip()
        current_buffer = []
        if not text:
            return

        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        working = ""
        for paragraph in paragraphs:
            candidate = paragraph if not working else f"{working}\n\n{paragraph}"
            if len(candidate) <= MAX_CHUNK_CHARS:
                working = candidate
                continue

            if working:
                chunk_index = _finalize_chunk(
                    chunks,
                    note_id=note_id,
                    chunk_index=chunk_index,
                    section_title=current_section,
                    content=working,
                    source_ref=source_ref,
                )
                working = ""

            if len(paragraph) <= MAX_CHUNK_CHARS:
                working = paragraph
                continue

            start = 0
            while start < len(paragraph):
                piece = paragraph[start : start + MAX_CHUNK_CHARS]
                chunk_index = _finalize_chunk(
                    chunks,
                    note_id=note_id,
                    chunk_index=chunk_index,
                    section_title=current_section,
                    content=piece,
                    source_ref=source_ref,
                )
                start += MAX_CHUNK_CHARS

        if working:
            chunk_index = _finalize_chunk(
                chunks,
                note_id=note_id,
                chunk_index=chunk_index,
                section_title=current_section,
                content=working,
                source_ref=source_ref,
            )

    for line in lines:
        heading_match = HEADING_RE.match(line.strip())
        if heading_match:
            flush_buffer()
            current_section = heading_match.group(2).strip() or current_section
            continue
        current_buffer.append(line)
        if sum(len(item) for item in current_buffer) >= MAX_CHUNK_CHARS + MIN_CHUNK_CHARS:
            flush_buffer()

    flush_buffer()

    if not chunks and content.strip():
        _finalize_chunk(
            chunks,
            note_id=note_id,
            chunk_index=chunk_index,
            section_title=current_section,
            content=content,
            source_ref=source_ref,
        )

    return chunks


def _replace_note_chunks_in_postgres(note_id: str, chunks: list[NoteChunk]) -> None:
    ensure_note_chunks_table()
    with _connect(autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {CHUNKS_TABLE_NAME} WHERE note_id = %s", (note_id,))
            for chunk in chunks:
                cur.execute(
                    f"""
                    INSERT INTO {CHUNKS_TABLE_NAME} (
                        chunk_id, note_id, chunk_index, section_title, content, char_count, source_ref, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        chunk.chunk_id,
                        chunk.note_id,
                        chunk.chunk_index,
                        chunk.section_title,
                        chunk.content,
                        chunk.char_count,
                        chunk.source_ref,
                    ),
                )
        conn.commit()


def _replace_note_chunks_in_qdrant(note_id: str, chunks: list[NoteChunk]) -> None:
    if not chunks:
        return

    embeddings = _get_embeddings()
    vectors = embeddings.embed_documents([chunk.content for chunk in chunks])
    if not vectors:
        return

    ensure_qdrant_collection(len(vectors[0]))
    client = _get_qdrant_client()
    collection_name = _get_qdrant_collection()

    client.delete(
        collection_name=collection_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="note_id",
                        match=models.MatchValue(value=note_id),
                    )
                ]
            )
        ),
    )

    points = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        points.append(
            models.PointStruct(
                id=str(uuid5(NAMESPACE_URL, chunk.chunk_id)),
                vector=vector,
                payload={
                    "chunk_id": chunk.chunk_id,
                    "note_id": chunk.note_id,
                    "chunk_index": chunk.chunk_index,
                    "section_title": chunk.section_title,
                    "content": chunk.content,
                    "char_count": chunk.char_count,
                    "source_ref": chunk.source_ref,
                },
            )
        )

    client.upsert(collection_name=collection_name, points=points)


def rebuild_note_rag_index(
    *,
    note_id: str,
    title: str,
    content: str,
    source_ref: str = "",
) -> int:
    chunks = split_markdown_into_chunks(
        note_id=note_id,
        title=title,
        content=content,
        source_ref=source_ref,
    )
    _replace_note_chunks_in_postgres(note_id, chunks)
    _replace_note_chunks_in_qdrant(note_id, chunks)
    logger.info("Indexed %s chunks for note '%s'.", len(chunks), note_id)
    return len(chunks)


def delete_note_rag_index(note_id: str) -> None:
    ensure_note_chunks_table()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {CHUNKS_TABLE_NAME} WHERE note_id = %s", (note_id,))

    client = _get_qdrant_client()
    collection_name = _get_qdrant_collection()
    if client.collection_exists(collection_name):
        client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="note_id",
                            match=models.MatchValue(value=note_id),
                        )
                    ]
                )
            ),
        )


def rebuild_all_note_rag_indexes() -> int:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT note_id, title, content, source_ref FROM notes ORDER BY updated_at DESC")
            rows = cur.fetchall()

    indexed = 0
    for note_id, title, content, source_ref in rows:
        rebuild_note_rag_index(
            note_id=note_id,
            title=title,
            content=content,
            source_ref=source_ref or "",
        )
        indexed += 1
    return indexed


def retrieve_note_chunks(
    *,
    query: str,
    limit: int = 5,
    note_id: Optional[str] = None,
) -> list[RetrievedChunk]:
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    client = _get_qdrant_client()
    collection_name = _get_qdrant_collection()
    if not client.collection_exists(collection_name):
        return []

    embedding = _get_embeddings().embed_query(cleaned_query)
    query_filter = None
    if note_id:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="note_id",
                    match=models.MatchValue(value=note_id),
                )
            ]
        )

    response = client.query_points(
        collection_name=collection_name,
        query=embedding,
        query_filter=query_filter,
        limit=max(limit, 1),
        with_payload=True,
    )
    results = response.points

    retrieved: list[RetrievedChunk] = []
    for item in results:
        payload = item.payload or {}
        retrieved.append(
            RetrievedChunk(
                chunk_id=str(payload.get("chunk_id") or ""),
                note_id=str(payload.get("note_id") or ""),
                chunk_index=int(payload.get("chunk_index") or 0),
                section_title=str(payload.get("section_title") or ""),
                content=str(payload.get("content") or ""),
                char_count=int(payload.get("char_count") or 0),
                source_ref=str(payload.get("source_ref") or ""),
                score=float(item.score),
            )
        )
    return retrieved


__all__ = [
    "NoteChunk",
    "RetrievedChunk",
    "split_markdown_into_chunks",
    "ensure_note_chunks_table",
    "ensure_qdrant_collection",
    "rebuild_note_rag_index",
    "rebuild_all_note_rag_indexes",
    "delete_note_rag_index",
    "retrieve_note_chunks",
]
