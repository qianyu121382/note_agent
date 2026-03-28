from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agent.tools.note_store import NoteConflictError, create_note, get_note, update_note


def test_update_note_detects_version_conflict() -> None:
    metadata = create_note(
        title="Concurrency Test",
        content="# Initial\n\nHello",
        summary="test",
        source_type="text",
    )

    record = get_note(metadata.note_id)
    assert record is not None
    initial_version = record.metadata.version

    updated = update_note(
        metadata.note_id,
        content="# Updated\n\nHello world",
        expected_version=initial_version,
    )
    assert updated is not None
    assert updated.version == initial_version + 1

    try:
        update_note(
            metadata.note_id,
            content="# Stale Update\n\nShould fail",
            expected_version=initial_version,
        )
        assert False, "Expected a NoteConflictError"
    except NoteConflictError as exc:
        assert exc.expected_version == initial_version
        assert exc.actual_version == initial_version + 1
