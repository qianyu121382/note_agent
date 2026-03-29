"""Dispatcher Node."""
from typing import Any, Dict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from agent.llm import llm
from agent.session_state import (
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
from agent.utils.logging import logger

from .prompts import create_dispatcher_prompt
from .schemas import DispatcherOutput

structured_llm = llm.with_structured_output(DispatcherOutput)
dispatcher_prompt = create_dispatcher_prompt()
dispatcher_chain = dispatcher_prompt | structured_llm


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


def _build_pending_context(
    *,
    user_input: str,
    mode: str,
    operation: str,
) -> dict[str, str]:
    return {
        "original_user_input": user_input,
        "mode": mode,
        "operation": operation,
    }


def _should_treat_as_new_request(user_input: str) -> bool:
    lowered = user_input.lower()
    if "http://" in lowered or "https://" in lowered:
        return True
    if any(drive in user_input for drive in ("C:\\", "D:\\", "E:\\")):
        return True
    return len(user_input.strip()) >= 120


def _try_resolve_pending_clarification(
    *,
    pending_clarification: str,
    pending_context: Dict[str, Any] | None,
    user_input: str,
) -> Dict[str, Any] | None:
    if pending_clarification == "note_target":
        if not user_input.strip():
            return None
        mode = normalize_mode((pending_context or {}).get("mode"))
        inferred_mode = mode if mode != "idle" else ("qa" if looks_like_qa_request(user_input) else "edit")
        return {
            "intent": "note_taking",
            "mode": inferred_mode,
            "operation": "locate_note",
            "extracted_data": [],
            "pending_clarification": "none",
            "pending_question": None,
            "pending_context": None,
        }

    if pending_clarification == "edit_operation":
        operation = resolve_operation(
            current_operation="none",
            mode="edit",
            intent="note_taking",
            user_input=user_input,
            has_extracted_data=False,
        )
        if operation in {"none", "general_follow_up", "locate_note", "create_note"}:
            return None
        mode = normalize_mode((pending_context or {}).get("mode"))
        return {
            "intent": "note_taking",
            "mode": mode if mode != "idle" else "edit",
            "operation": operation,
            "extracted_data": [],
            "pending_clarification": "none",
            "pending_question": None,
            "pending_context": None,
        }

    return None


def _maybe_request_clarification(
    *,
    user_input: str,
    active_note_id: str | None,
    has_extracted_data: bool,
    mode: str,
    operation: str,
) -> Dict[str, Any] | None:
    if should_request_note_target_clarification(
        user_input=user_input,
        has_active_note=bool(active_note_id),
    ):
        prompt = _build_clarification_prompt("note_target", user_input)
        return {
            "intent": "waiting",
            "mode": mode,
            "operation": operation,
            "extracted_data": [],
            "pending_clarification": "note_target",
            "pending_question": prompt,
            "pending_context": _build_pending_context(
                user_input=user_input,
                mode="qa" if looks_like_qa_request(user_input) else "edit",
                operation="locate_note",
            ),
            "messages": [AIMessage(content=prompt)],
        }

    if should_request_edit_operation_clarification(
        user_input=user_input,
        has_active_note=bool(active_note_id),
        has_extracted_data=has_extracted_data,
    ):
        prompt = _build_clarification_prompt("edit_operation", user_input)
        return {
            "intent": "waiting",
            "mode": mode,
            "operation": operation,
            "extracted_data": [],
            "pending_clarification": "edit_operation",
            "pending_question": prompt,
            "pending_context": _build_pending_context(
                user_input=user_input,
                mode="edit",
                operation="general_follow_up",
            ),
            "messages": [AIMessage(content=prompt)],
        }

    return None


def _extract_user_input(state: Dict[str, Any]) -> str:
    """
    Support both CLI-style input (`user_input`) and LangGraph server / chat UI input (`messages`).
    """
    user_input = state.get("user_input", "")
    if isinstance(user_input, str) and user_input.strip():
        return user_input.strip()

    messages = state.get("messages", [])
    if not isinstance(messages, list):
        return ""

    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            content = message.content
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                parts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                text = "".join(parts).strip()
                if text:
                    return text
        elif isinstance(message, BaseMessage) and getattr(message, "type", None) == "human":
            content = getattr(message, "content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                parts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                text = "".join(parts).strip()
                if text:
                    return text
        elif isinstance(message, dict):
            role = message.get("type") or message.get("role")
            if role not in {"human", "user"}:
                continue
            content = message.get("content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
                text = "".join(parts).strip()
                if text:
                    return text

    return ""


def _route_existing_note_request(
    *,
    user_input: str,
    active_note_id: str | None,
    current_operation: str,
) -> dict[str, Any] | None:
    has_note_reference = looks_like_note_reference(user_input) or looks_like_note_lookup_request(user_input)
    if not has_note_reference:
        return None

    if active_note_id and looks_like_edit_request(user_input):
        logger.info(
            "Detected follow-up edit request with active note '%s'. Routing directly to note_taking/edit.",
            active_note_id,
        )
        mode = "edit"
        return {
            "intent": "note_taking",
            "mode": mode,
            "operation": resolve_operation(
                current_operation=current_operation,
                mode=mode,
                intent="note_taking",
                user_input=user_input,
                has_extracted_data=False,
            ),
            "extracted_data": [],
            "pending_clarification": "none",
            "pending_question": None,
            "pending_context": None,
        }

    if active_note_id and looks_like_qa_request(user_input):
        logger.info(
            "Detected follow-up QA request with active note '%s'. Routing directly to note_taking/qa.",
            active_note_id,
        )
        mode = "qa"
        return {
            "intent": "note_taking",
            "mode": mode,
            "operation": resolve_operation(
                current_operation=current_operation,
                mode=mode,
                intent="note_taking",
                user_input=user_input,
                has_extracted_data=False,
            ),
            "extracted_data": [],
            "pending_clarification": "none",
            "pending_question": None,
            "pending_context": None,
        }

    if looks_like_note_lookup_request(user_input) or (not active_note_id and has_note_reference):
        inferred_mode = "qa" if looks_like_qa_request(user_input) else "edit"
        logger.info(
            "Detected existing-note request without active note. Routing to note_taking/locate_note with inferred mode '%s'.",
            inferred_mode,
        )
        return {
            "intent": "note_taking",
            "mode": inferred_mode,
            "operation": "locate_note",
            "extracted_data": [],
            "pending_clarification": "none",
            "pending_question": None,
            "pending_context": None,
        }

    return None


def dispatch(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the user input, determine intent, and extract useful content."""
    logger.info("--- Node: Dispatcher ---")
    user_input = _extract_user_input(state)
    current_mode = normalize_mode(state.get("mode"))
    current_operation = normalize_operation(state.get("operation"))
    pending_clarification = normalize_pending_clarification(state.get("pending_clarification"))
    pending_question = state.get("pending_question")
    pending_context = state.get("pending_context")

    if not user_input:
        logger.warning("User input is empty.")
        return {
            "intent": "waiting",
            "mode": current_mode,
            "operation": current_operation,
            "extracted_data": [],
            "pending_clarification": pending_clarification,
            "pending_question": pending_question,
            "pending_context": pending_context,
        }

    logger.info(f"Analyzing user input: '{user_input[:80]}...'")

    if pending_clarification != "none" and not _should_treat_as_new_request(user_input):
        clarification_result = _try_resolve_pending_clarification(
            pending_clarification=pending_clarification,
            pending_context=pending_context if isinstance(pending_context, dict) else None,
            user_input=user_input,
        )
        if clarification_result is not None:
            logger.info("Resolved pending clarification '%s' from user reply.", pending_clarification)
            return clarification_result

    active_note_id = state.get("active_note_id")
    existing_note_route = _route_existing_note_request(
        user_input=user_input,
        active_note_id=active_note_id,
        current_operation=current_operation,
    )
    if existing_note_route is not None:
        return existing_note_route

    response: DispatcherOutput = dispatcher_chain.invoke({"user_input": user_input})

    logger.info(f"LLM analysis complete. Intent: '{response.intent}'")
    if response.intent == "waiting":
        logger.debug(f"LLM generated response for user: '{response.response_to_user}'")

    if response.data:
        for item in response.data:
            logger.debug(f"Extracted data: type='{item.type}', content='{item.content[:100]}...'")

    mode = resolve_mode(
        current_mode=current_mode,
        intent=response.intent,
        user_input=user_input,
        has_active_note=bool(active_note_id),
        has_extracted_data=bool(response.data),
    )
    operation = resolve_operation(
        current_operation=current_operation,
        mode=mode,
        intent=response.intent,
        user_input=user_input,
        has_extracted_data=bool(response.data),
        llm_operation=response.operation,
    )

    clarification_request = _maybe_request_clarification(
        user_input=user_input,
        active_note_id=active_note_id,
        has_extracted_data=bool(response.data),
        mode=mode,
        operation=operation,
    )
    if clarification_request is not None:
        logger.info(
            "Request requires clarification '%s' before continuing.",
            clarification_request["pending_clarification"],
        )
        return clarification_request

    result = {
        "intent": response.intent,
        "mode": mode,
        "operation": operation,
        "extracted_data": response.data,
        "pending_clarification": "none",
        "pending_question": None,
        "pending_context": None,
    }
    if response.intent == "waiting" and response.response_to_user:
        result["messages"] = [AIMessage(content=response.response_to_user)]

    return result
