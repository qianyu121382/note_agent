from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage

from agent.session_state import (
    looks_like_qa_request,
    normalize_mode,
    normalize_pending_clarification,
    resolve_operation,
    should_request_edit_operation_clarification,
    should_request_note_target_clarification,
)


def _prefers_chinese(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _build_clarification_prompt(kind: str, user_input: str) -> str:
    zh = _prefers_chinese(user_input)
    if kind == "note_target":
        return (
            "\u4f60\u60f3\u5904\u7406\u54ea\u4e00\u7bc7\u7b14\u8bb0\uff1f\u8bf7\u76f4\u63a5\u544a\u8bc9\u6211\u6807\u9898\u5173\u952e\u8bcd\u3001`note_id`\uff0c\u6216\u8005\u63cf\u8ff0\u4f8b\u5982\u201cRAG \u90a3\u7bc7\u201d\u3002"
            if zh
            else "Which note do you want to work on? Please give me a title keyword, `note_id`, or a hint like 'the RAG one'."
        )
    if kind == "edit_operation":
        return (
            "\u4f60\u60f3\u5bf9\u8fd9\u7bc7\u7b14\u8bb0\u505a\u4ec0\u4e48\u64cd\u4f5c\uff1f\u4f8b\u5982\uff1a\u6269\u5199\u3001\u7cbe\u7b80\u3001\u7ffb\u8bd1\u3001\u6539\u6210\u63d0\u7eb2\u3001\u91cd\u5199\u3002"
            if zh
            else "What do you want to do with this note? For example: expand, condense, translate, outline, or rewrite."
        )
    return "Please clarify your request."


def _build_pending_context(*, user_input: str, mode: str, operation: str) -> dict[str, str]:
    return {
        "original_user_input": user_input,
        "mode": mode,
        "operation": operation,
    }


def should_treat_as_new_request(user_input: str) -> bool:
    lowered = user_input.lower()
    if "http://" in lowered or "https://" in lowered:
        return True
    if any(drive in user_input for drive in ("C:\\", "D:\\", "E:\\")):
        return True
    return len(user_input.strip()) >= 120


@dataclass(frozen=True)
class ClarificationState:
    kind: str = "none"
    question: str | None = None
    context: dict[str, Any] | None = None

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "ClarificationState":
        raw_context = state.get("pending_context")
        return cls(
            kind=normalize_pending_clarification(state.get("pending_clarification")),
            question=state.get("pending_question") if isinstance(state.get("pending_question"), str) else None,
            context=raw_context if isinstance(raw_context, dict) else None,
        )

    @property
    def is_pending(self) -> bool:
        return self.kind != "none"

    def clear_patch(self) -> dict[str, Any]:
        return {
            "pending_clarification": "none",
            "pending_question": None,
            "pending_context": None,
        }

    def try_resolve(self, user_input: str) -> dict[str, Any] | None:
        if self.kind == "note_target":
            if not user_input.strip():
                return None
            mode = normalize_mode((self.context or {}).get("mode"))
            inferred_mode = mode if mode != "idle" else ("qa" if looks_like_qa_request(user_input) else "edit")
            return {
                "intent": "note_taking",
                "mode": inferred_mode,
                "operation": "locate_note",
                "extracted_data": [],
                **self.clear_patch(),
            }

        if self.kind == "edit_operation":
            operation = resolve_operation(
                current_operation="none",
                mode="edit",
                intent="note_taking",
                user_input=user_input,
                has_extracted_data=False,
            )
            if operation in {"none", "general_follow_up", "locate_note", "create_note"}:
                return None
            mode = normalize_mode((self.context or {}).get("mode"))
            return {
                "intent": "note_taking",
                "mode": mode if mode != "idle" else "edit",
                "operation": operation,
                "extracted_data": [],
                **self.clear_patch(),
            }

        return None

    @classmethod
    def maybe_request(
        cls,
        *,
        user_input: str,
        active_note_id: str | None,
        has_extracted_data: bool,
        mode: str,
        operation: str,
    ) -> dict[str, Any] | None:
        if should_request_note_target_clarification(
            user_input=user_input,
            has_active_note=bool(active_note_id),
        ):
            clarification = cls(
                kind="note_target",
                question=_build_clarification_prompt("note_target", user_input),
                context=_build_pending_context(
                    user_input=user_input,
                    mode="qa" if looks_like_qa_request(user_input) else "edit",
                    operation="locate_note",
                ),
            )
            return clarification.as_waiting_patch(mode=mode, operation=operation)

        if should_request_edit_operation_clarification(
            user_input=user_input,
            has_active_note=bool(active_note_id),
            has_extracted_data=has_extracted_data,
        ):
            clarification = cls(
                kind="edit_operation",
                question=_build_clarification_prompt("edit_operation", user_input),
                context=_build_pending_context(
                    user_input=user_input,
                    mode="edit",
                    operation="general_follow_up",
                ),
            )
            return clarification.as_waiting_patch(mode=mode, operation=operation)

        return None

    def as_waiting_patch(self, *, mode: str, operation: str) -> dict[str, Any]:
        prompt = self.question or "Please clarify your request."
        return {
            "intent": "waiting",
            "mode": mode,
            "operation": operation,
            "extracted_data": [],
            "pending_clarification": self.kind,
            "pending_question": prompt,
            "pending_context": self.context,
            "messages": [AIMessage(content=prompt)],
        }


__all__ = ["ClarificationState", "should_treat_as_new_request"]
