from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agent.tools.note_store import (
    NoteMetadata,
    NoteRecord,
    create_note as create_note_in_store,
    delete_note as delete_note_in_store,
    get_note,
    list_notes,
    search_notes,
    set_note_rag_indexed,
    update_note as update_note_in_store,
)
from agent.tools.rag_store import (
    delete_note_rag_index,
    rebuild_all_note_rag_indexes,
    rebuild_note_rag_index,
)


@dataclass
class NoteService:
    """
    Minimal business orchestration layer for note CRUD + derived RAG index sync.
    PostgreSQL notes remain the source of truth; chunk/vector indexes are derived.
    """

    def create_note(
        self,
        *,
        title: str,
        content: str,
        summary: str = "",
        tags: Optional[list[str]] = None,
        source_type: str = "text",
        source_ref: str = "",
        thread_id: str | None = None,
    ) -> NoteMetadata:
        metadata = create_note_in_store(
            title=title,
            content=content,
            summary=summary,
            tags=tags,
            source_type=source_type,
            source_ref=source_ref,
            thread_id=thread_id,
        )
        self._sync_rag_index(
            note_id=metadata.note_id,
            title=metadata.title,
            content=content,
            source_ref=metadata.source_ref,
        )
        return metadata

    def get_note(self, note_id: str) -> NoteRecord | None:
        return get_note(note_id)

    def update_note(
        self,
        note_id: str,
        *,
        content: str,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
        thread_id: str | None = None,
        last_modified_from: str = "edit",
        expected_version: int | None = None,
    ) -> NoteMetadata | None:
        metadata = update_note_in_store(
            note_id,
            content=content,
            title=title,
            summary=summary,
            tags=tags,
            thread_id=thread_id,
            last_modified_from=last_modified_from,
            expected_version=expected_version,
        )
        if metadata is None:
            return None

        self._sync_rag_index(
            note_id=metadata.note_id,
            title=metadata.title,
            content=content,
            source_ref=metadata.source_ref,
        )
        return metadata

    def delete_note(self, note_id: str) -> NoteMetadata | None:
        metadata = delete_note_in_store(note_id)
        if metadata is None:
            return None
        delete_note_rag_index(note_id)
        return metadata

    def list_notes(self, limit: int = 20):
        return list_notes(limit=limit)

    def search_notes(self, query: str, limit: int = 5):
        return search_notes(query=query, limit=limit)

    def rebuild_all_indexes(self) -> int:
        count = rebuild_all_note_rag_indexes()
        for note in self.list_notes(limit=100000):
            note_id = note.get("note_id")
            if note_id:
                set_note_rag_indexed(str(note_id), True)
        return count

    def _sync_rag_index(self, *, note_id: str, title: str, content: str, source_ref: str = "") -> None:
        try:
            rebuild_note_rag_index(
                note_id=note_id,
                title=title,
                content=content,
                source_ref=source_ref or "",
            )
            set_note_rag_indexed(note_id, True)
        except Exception:
            set_note_rag_indexed(note_id, False)
            raise


_note_service = NoteService()


def get_note_service() -> NoteService:
    return _note_service


__all__ = [
    "NoteService",
    "get_note_service",
]
