"""Utilities for managing thread-scoped session state."""
from __future__ import annotations

import re
from typing import Any

from agent.state import (
    AGENT_MODES,
    AGENT_OPERATIONS,
    PENDING_CLARIFICATIONS,
    AgentMode,
    AgentOperation,
    PendingClarification,
)

EDIT_KEYWORDS = {
    "modify",
    "edit",
    "update",
    "rewrite",
    "revise",
    "expand",
    "shorten",
    "translate",
    "polish",
    "refine",
    "improve",
    "change",
    "补充",
    "修改",
    "改",
    "重写",
    "润色",
    "扩写",
    "精简",
    "翻译",
    "完善",
    "处理",
}

QA_KEYWORDS = {
    "summary",
    "summarize",
    "explain",
    "what",
    "why",
    "how",
    "question",
    "总结",
    "概括",
    "主要讲",
    "是什么",
    "解释",
    "问答",
    "区别",
    "对比",
    "核心",
    "要点",
}

NOTE_REFERENCE_KEYWORDS = {
    "note",
    "notes",
    "last note",
    "previous note",
    "that note",
    "this note",
    "上一篇",
    "上一版",
    "刚才那篇",
    "刚刚那篇",
    "这篇",
    "那篇",
    "笔记",
}

NOTE_LOOKUP_KEYWORDS = {
    "find note",
    "locate note",
    "which note",
    "search note",
    "list notes",
    "show notes",
    "找笔记",
    "定位笔记",
    "哪篇笔记",
    "搜索笔记",
    "列出笔记",
    "有哪些笔记",
    "哪篇",
}

AMBIGUOUS_NOTE_TARGET_KEYWORDS = {
    "last note",
    "previous note",
    "that note",
    "this note",
    "上一篇",
    "上一版",
    "刚才那篇",
    "刚刚那篇",
    "这篇",
    "那篇",
}

GENERIC_CLARIFICATION_FILLERS = (
    "帮我",
    "一下",
    "这篇",
    "那篇",
    "上一篇",
    "上一版",
    "刚才那篇",
    "刚刚那篇",
    "笔记",
    "note",
    "notes",
    "this note",
    "that note",
    "last note",
    "previous note",
    "modify",
    "edit",
    "update",
    "rewrite",
    "revise",
    "translate",
    "summary",
    "summarize",
    "解释",
    "说明",
    "修改",
    "改",
    "翻译",
    "总结",
    "处理",
)

OPERATION_KEYWORDS: dict[AgentOperation, set[str]] = {
    "locate_note": {
        "find note",
        "locate note",
        "search note",
        "which note",
        "找笔记",
        "定位笔记",
        "搜索笔记",
        "哪篇笔记",
        "上一篇",
        "刚才那篇",
        "这篇",
        "那篇",
    },
    "expand_note": {"expand", "detailed", "detail", "扩写", "详细", "展开", "补充"},
    "condense_note": {"shorten", "condense", "brief", "压缩", "精简", "简洁", "简短"},
    "translate_note": {"translate", "translation", "翻译", "中文", "英文"},
    "outline_note": {"outline", "提纲", "大纲", "结构化"},
    "rewrite_note": {"rewrite", "revise", "重写", "改写", "重构"},
    "summarize_note": {"summary", "summarize", "总结", "概括", "摘要"},
    "explain_note": {"explain", "解释", "说明", "讲讲", "什么意思"},
    "extract_points": {"points", "key points", "要点", "重点", "三点", "核心观点"},
}


def normalize_mode(value: Any) -> AgentMode:
    if isinstance(value, str) and value in AGENT_MODES:
        return value
    return "idle"


def normalize_operation(value: Any) -> AgentOperation:
    if isinstance(value, str) and value in AGENT_OPERATIONS:
        return value
    return "none"


def normalize_pending_clarification(value: Any) -> PendingClarification:
    if isinstance(value, str) and value in PENDING_CLARIFICATIONS:
        return value
    return "none"


def _contains_any(user_input: str, keywords: set[str]) -> bool:
    lowered = user_input.lower()
    return any(keyword in lowered for keyword in keywords)


def _strip_generic_clarification_terms(user_input: str) -> str:
    lowered = user_input.lower()
    for filler in GENERIC_CLARIFICATION_FILLERS:
        lowered = lowered.replace(filler, " ")
    lowered = re.sub(r"[\s,，。.!！?？:：/\\-]+", " ", lowered)
    return lowered.strip()


def looks_like_edit_request(user_input: str) -> bool:
    return _contains_any(user_input, EDIT_KEYWORDS)


def looks_like_qa_request(user_input: str) -> bool:
    return _contains_any(user_input, QA_KEYWORDS)


def looks_like_note_reference(user_input: str) -> bool:
    return _contains_any(user_input, NOTE_REFERENCE_KEYWORDS)


def looks_like_note_lookup_request(user_input: str) -> bool:
    return _contains_any(user_input, NOTE_LOOKUP_KEYWORDS)


def looks_like_ambiguous_note_target(user_input: str) -> bool:
    return _contains_any(user_input, AMBIGUOUS_NOTE_TARGET_KEYWORDS)


def has_explicit_note_target_hint(user_input: str) -> bool:
    cleaned = _strip_generic_clarification_terms(user_input)
    return bool(re.search(r"[A-Za-z0-9\u4e00-\u9fff]{2,}", cleaned))


def _match_operation_keyword(user_input: str) -> AgentOperation | None:
    lowered = user_input.lower()
    for operation, keywords in OPERATION_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return operation
    return None


def should_request_note_target_clarification(
    *,
    user_input: str,
    has_active_note: bool,
) -> bool:
    if has_active_note:
        return False
    if not looks_like_ambiguous_note_target(user_input):
        return False
    return not has_explicit_note_target_hint(user_input)


def should_request_edit_operation_clarification(
    *,
    user_input: str,
    has_active_note: bool,
    has_extracted_data: bool,
) -> bool:
    if not has_active_note or has_extracted_data:
        return False
    if not looks_like_edit_request(user_input):
        return False

    lowered = user_input.lower()
    for operation in (
        "expand_note",
        "condense_note",
        "translate_note",
        "outline_note",
        "rewrite_note",
    ):
        if any(keyword in lowered for keyword in OPERATION_KEYWORDS[operation]):
            return False

    return True


def resolve_mode(
    *,
    current_mode: Any,
    intent: str,
    user_input: str,
    has_active_note: bool,
    has_extracted_data: bool,
) -> AgentMode:
    resolved_current_mode = normalize_mode(current_mode)

    if intent == "exit":
        return "idle"

    if intent != "note_taking":
        return resolved_current_mode

    if has_extracted_data:
        return "create"

    if looks_like_qa_request(user_input):
        return "qa"

    if looks_like_edit_request(user_input):
        return "edit"

    if has_active_note and resolved_current_mode in {"edit", "qa"}:
        return resolved_current_mode

    if resolved_current_mode in {"create", "edit", "qa"}:
        return resolved_current_mode

    return "create"


def resolve_operation(
    *,
    current_operation: Any,
    mode: Any,
    intent: str,
    user_input: str,
    has_extracted_data: bool,
    llm_operation: Any = None,
) -> AgentOperation:
    resolved_mode = normalize_mode(mode)
    normalized_llm_operation = normalize_operation(llm_operation)
    if normalized_llm_operation != "none":
        return normalized_llm_operation

    if intent != "note_taking":
        return normalize_operation(current_operation)

    if has_extracted_data or resolved_mode == "create":
        return "create_note"

    keyword_operation = _match_operation_keyword(user_input)
    if keyword_operation is not None:
        return keyword_operation

    if resolved_mode in {"edit", "qa"}:
        if looks_like_note_reference(user_input) or looks_like_note_lookup_request(user_input):
            return "locate_note"
        return "general_follow_up"

    return normalize_operation(current_operation)


__all__ = [
    "normalize_mode",
    "normalize_operation",
    "normalize_pending_clarification",
    "looks_like_edit_request",
    "looks_like_qa_request",
    "looks_like_note_reference",
    "looks_like_note_lookup_request",
    "looks_like_ambiguous_note_target",
    "has_explicit_note_target_hint",
    "should_request_note_target_clarification",
    "should_request_edit_operation_clarification",
    "resolve_mode",
    "resolve_operation",
]
