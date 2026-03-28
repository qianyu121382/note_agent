from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agent.tools.note_store import create_note, search_notes


def test_search_notes_returns_relevant_candidates() -> None:
    create_note(
        title="LangGraph RAG Notes",
        content="# RAG\n\nAbout retrieval",
        summary="RAG pipeline notes",
        source_type="text",
    )
    create_note(
        title="Agent Runtime Notes",
        content="# Agent\n\nAbout runtime",
        summary="Agent design notes",
        source_type="text",
    )

    matches = search_notes("RAG", limit=3)
    assert matches
    assert "RAG" in str(matches[0].get("title", ""))
