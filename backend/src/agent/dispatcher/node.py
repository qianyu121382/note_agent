"""Dispatcher Node."""
from typing import Any, Dict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from agent.llm import llm
from agent.utils.logging import logger

from .prompts import create_dispatcher_prompt
from .schemas import DispatcherOutput

structured_llm = llm.with_structured_output(DispatcherOutput)
dispatcher_prompt = create_dispatcher_prompt()
dispatcher_chain = dispatcher_prompt | structured_llm

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
    "刚才",
    "这篇",
    "上一篇",
    "刚刚",
}


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


def _looks_like_edit_request(user_input: str) -> bool:
    lowered = user_input.lower()
    return any(keyword in lowered for keyword in EDIT_KEYWORDS)


def dispatch(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the user input, determine intent, and extract useful content."""
    logger.info("--- Node: Dispatcher ---")
    user_input = _extract_user_input(state)
    if not user_input:
        logger.warning("User input is empty.")
        return {"intent": "waiting", "extracted_data": []}

    logger.info(f"Analyzing user input: '{user_input[:80]}...'")

    active_note_id = state.get("active_note_id")
    if active_note_id and _looks_like_edit_request(user_input):
        logger.info(
            "Detected follow-up edit request with active note '%s'. Routing directly to note_taking.",
            active_note_id,
        )
        return {
            "intent": "note_taking",
            "extracted_data": [],
        }

    response: DispatcherOutput = dispatcher_chain.invoke({"user_input": user_input})

    logger.info(f"LLM analysis complete. Intent: '{response.intent}'")
    if response.intent == "waiting":
        logger.debug(f"LLM generated response for user: '{response.response_to_user}'")

    if response.data:
        for item in response.data:
            logger.debug(f"Extracted data: type='{item.type}', content='{item.content[:100]}...'")

    result = {"intent": response.intent, "extracted_data": response.data}
    if response.intent == "waiting" and response.response_to_user:
        result["messages"] = [AIMessage(content=response.response_to_user)]

    return result
