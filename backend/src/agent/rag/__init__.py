from __future__ import annotations

from agent.tools.note_store import search_notes
from agent.tools.rag_store import retrieve_note_chunks


def search_notes_for_baseline(*, query: str, limit: int = 5):
    """
    Legacy compatibility wrapper for note lookup.
    Note lookup remains metadata-based and is separate from chunk retrieval.
    """
    return search_notes(query=query, limit=limit)


def retrieve_chunks_for_baseline(*, query: str, note_id: str | None = None, limit: int = 5):
    """
    Legacy compatibility wrapper for RAG retrieval.
    Current baseline is global chunk retrieval; note_id is optional.
    """
    return retrieve_note_chunks(query=query, note_id=note_id, limit=limit)


__all__ = [
    "search_notes_for_baseline",
    "retrieve_chunks_for_baseline",
]
