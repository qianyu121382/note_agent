from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agent.session_state import (
    has_explicit_note_target_hint,
    looks_like_ambiguous_note_target,
    looks_like_edit_request,
    looks_like_note_lookup_request,
    looks_like_note_reference,
    looks_like_qa_request,
    normalize_mode,
    normalize_operation,
    normalize_pending_clarification,
    resolve_mode,
    resolve_operation,
    should_request_edit_operation_clarification,
    should_request_note_target_clarification,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("idle", "idle"),
        ("create", "create"),
        ("edit", "edit"),
        ("qa", "qa"),
        ("unknown", "idle"),
        (None, "idle"),
    ],
)
def test_normalize_mode(value, expected) -> None:
    assert normalize_mode(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("create_note", "create_note"),
        ("locate_note", "locate_note"),
        ("translate_note", "translate_note"),
        ("none", "none"),
        ("unknown", "none"),
        (None, "none"),
    ],
)
def test_normalize_operation(value, expected) -> None:
    assert normalize_operation(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("none", "none"),
        ("note_target", "note_target"),
        ("edit_operation", "edit_operation"),
        ("unknown", "none"),
        (None, "none"),
    ],
)
def test_normalize_pending_clarification(value, expected) -> None:
    assert normalize_pending_clarification(value) == expected


def test_resolve_mode_prefers_create_when_new_content_exists() -> None:
    assert resolve_mode(
        current_mode="idle",
        intent="note_taking",
        user_input="请整理这段文本",
        has_active_note=False,
        has_extracted_data=True,
    ) == "create"


def test_resolve_mode_uses_edit_for_active_note_follow_up() -> None:
    assert looks_like_edit_request("把这篇改详细一点")
    assert resolve_mode(
        current_mode="create",
        intent="note_taking",
        user_input="把这篇改详细一点",
        has_active_note=True,
        has_extracted_data=False,
    ) == "edit"


def test_resolve_mode_uses_qa_for_active_note_question() -> None:
    assert looks_like_qa_request("总结一下这篇笔记的核心观点")
    assert resolve_mode(
        current_mode="edit",
        intent="note_taking",
        user_input="总结一下这篇笔记的核心观点",
        has_active_note=True,
        has_extracted_data=False,
    ) == "qa"


def test_resolve_mode_infers_edit_without_active_note_when_revising_existing_note() -> None:
    assert resolve_mode(
        current_mode="idle",
        intent="note_taking",
        user_input="帮我修改 RAG 那篇笔记",
        has_active_note=False,
        has_extracted_data=False,
    ) == "edit"


def test_resolve_mode_preserves_current_mode_when_not_note_taking() -> None:
    assert resolve_mode(
        current_mode="edit",
        intent="waiting",
        user_input="你好",
        has_active_note=True,
        has_extracted_data=False,
    ) == "edit"


def test_note_lookup_helpers_detect_existing_note_references() -> None:
    assert looks_like_note_reference("把上一篇笔记改详细一点")
    assert looks_like_note_lookup_request("帮我找一下 RAG 那篇笔记")


def test_ambiguous_note_target_detection_distinguishes_explicit_hint() -> None:
    assert looks_like_ambiguous_note_target("帮我改一下这篇")
    assert not has_explicit_note_target_hint("帮我改一下这篇")
    assert has_explicit_note_target_hint("帮我找一下 RAG 那篇笔记")


def test_should_request_note_target_clarification_for_ambiguous_follow_up() -> None:
    assert should_request_note_target_clarification(
        user_input="帮我改一下这篇",
        has_active_note=False,
    )


def test_should_not_request_note_target_clarification_when_active_note_exists() -> None:
    assert not should_request_note_target_clarification(
        user_input="把这篇改详细一点",
        has_active_note=True,
    )


def test_should_request_edit_operation_clarification_for_generic_edit() -> None:
    assert should_request_edit_operation_clarification(
        user_input="帮我改一下这篇笔记",
        has_active_note=True,
        has_extracted_data=False,
    )


def test_should_not_request_edit_operation_clarification_for_specific_edit() -> None:
    assert not should_request_edit_operation_clarification(
        user_input="把这篇翻译成中文",
        has_active_note=True,
        has_extracted_data=False,
    )


def test_resolve_operation_prefers_create_note_for_new_material() -> None:
    assert resolve_operation(
        current_operation="none",
        mode="create",
        intent="note_taking",
        user_input="请整理这段资料",
        has_extracted_data=True,
    ) == "create_note"


def test_resolve_operation_detects_locate_note_for_existing_note_lookup() -> None:
    assert resolve_operation(
        current_operation="none",
        mode="edit",
        intent="note_taking",
        user_input="帮我找一下 RAG 那篇笔记",
        has_extracted_data=False,
    ) == "locate_note"


def test_resolve_operation_detects_expand_note() -> None:
    assert resolve_operation(
        current_operation="none",
        mode="edit",
        intent="note_taking",
        user_input="把这篇改详细一点",
        has_extracted_data=False,
    ) == "expand_note"


def test_resolve_operation_detects_translate_note() -> None:
    assert resolve_operation(
        current_operation="none",
        mode="edit",
        intent="note_taking",
        user_input="把上一篇翻译成中文",
        has_extracted_data=False,
    ) == "translate_note"


def test_resolve_operation_detects_summarize_note() -> None:
    assert resolve_operation(
        current_operation="none",
        mode="qa",
        intent="note_taking",
        user_input="总结一下这篇笔记",
        has_extracted_data=False,
    ) == "summarize_note"


def test_resolve_operation_falls_back_to_general_follow_up() -> None:
    assert resolve_operation(
        current_operation="none",
        mode="edit",
        intent="note_taking",
        user_input="就按刚才那个来",
        has_extracted_data=False,
    ) == "general_follow_up"
