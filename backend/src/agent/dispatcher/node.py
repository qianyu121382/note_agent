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
    resolve_mode,
    resolve_operation,
)
from agent.utils.logging import logger

from .prompts import create_dispatcher_prompt
from .schemas import DispatcherOutput

structured_llm = llm.with_structured_output(DispatcherOutput)
dispatcher_prompt = create_dispatcher_prompt()
dispatcher_chain = dispatcher_prompt | structured_llm



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
        }

    return None



def dispatch(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the user input, determine intent, and extract useful content."""
    logger.info("--- Node: Dispatcher ---")
    user_input = _extract_user_input(state)
    current_mode = normalize_mode(state.get("mode"))
    current_operation = normalize_operation(state.get("operation"))
    if not user_input:
        logger.warning("User input is empty.")
        return {
            "intent": "waiting",
            "mode": current_mode,
            "operation": current_operation,
            "extracted_data": [],
        }

    logger.info(f"Analyzing user input: '{user_input[:80]}...'")

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
    result = {
        "intent": response.intent,
        "mode": mode,
        "operation": operation,
        "extracted_data": response.data,
    }
    if response.intent == "waiting" and response.response_to_user:
        result["messages"] = [AIMessage(content=response.response_to_user)]

    return result
