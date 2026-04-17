from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agent.clarification import ClarificationState, should_treat_as_new_request


def test_clarification_state_from_state_normalizes_pending_fields() -> None:
    clarification = ClarificationState.from_state(
        {
            "pending_clarification": "edit_operation",
            "pending_question": "How should I update it?",
            "pending_context": {"mode": "edit", "operation": "general_follow_up"},
        }
    )

    assert clarification.kind == "edit_operation"
    assert clarification.question == "How should I update it?"
    assert clarification.context == {"mode": "edit", "operation": "general_follow_up"}
    assert clarification.is_pending is True


def test_clarification_state_resolves_note_target_reply() -> None:
    clarification = ClarificationState(
        kind="note_target",
        question="Which note do you want to work on?",
        context={"mode": "qa", "operation": "locate_note"},
    )

    resolved = clarification.try_resolve("RAG 那篇")

    assert resolved == {
        "intent": "note_taking",
        "mode": "qa",
        "operation": "locate_note",
        "extracted_data": [],
        "pending_clarification": "none",
        "pending_question": None,
        "pending_context": None,
    }


def test_clarification_state_requests_edit_operation_without_new_fields() -> None:
    request = ClarificationState.maybe_request(
        user_input="帮我改一下这篇笔记",
        active_note_id="note-123",
        has_extracted_data=False,
        mode="edit",
        operation="general_follow_up",
    )

    assert request is not None
    assert request["pending_clarification"] == "edit_operation"
    assert request["pending_question"]
    assert request["pending_context"] == {
        "original_user_input": "帮我改一下这篇笔记",
        "mode": "edit",
        "operation": "general_follow_up",
    }
    assert request["messages"][0].content == request["pending_question"]


def test_should_treat_as_new_request_detects_long_text_and_url() -> None:
    assert should_treat_as_new_request("https://example.com/article")
    assert should_treat_as_new_request("a" * 120)
    assert not should_treat_as_new_request("RAG 那篇")
