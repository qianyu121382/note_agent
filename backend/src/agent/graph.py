"""
Defines the main, simplified workflow for the Note Agent.
The architecture is: Restore Session -> Dispatcher -> (if needed) ReAct Agent -> Save Session -> END
"""
import re
import sys
from pathlib import Path
from typing import Any, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

# Ensure the `src` directory is importable when LangGraph loads this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.dispatcher import dispatch
from agent.react_agent.graph import base_prompt, react_agent_graph
from agent.session_store import load_session, save_session
from agent.state import AgentState
from agent.utils.logging import logger

NOTE_ID_RE = re.compile(r"note_id '([^']+)'")
TITLE_RE = re.compile(r"note '([^']+)'")


def _extract_thread_id(config: RunnableConfig | None) -> Optional[str]:
    if not config:
        return None
    configurable = config.get("configurable", {})
    if not isinstance(configurable, dict):
        return None
    thread_id = configurable.get("thread_id")
    return str(thread_id) if thread_id else None


def _message_signature(message: BaseMessage) -> tuple[str, str]:
    return (getattr(message, "type", message.__class__.__name__), str(getattr(message, "content", "")))


def _merge_messages(
    persisted_messages: list[BaseMessage],
    incoming_messages: list[BaseMessage],
) -> list[BaseMessage]:
    if not persisted_messages:
        return list(incoming_messages)
    if not incoming_messages:
        return list(persisted_messages)

    if len(incoming_messages) > 1:
        return list(incoming_messages)

    persisted_signatures = {_message_signature(message) for message in persisted_messages}
    merged = list(persisted_messages)
    for message in incoming_messages:
        if _message_signature(message) not in persisted_signatures:
            merged.append(message)
    return merged


def _get_latest_user_input(messages: List[BaseMessage]) -> str:
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


def _get_conversation_history(messages: List[BaseMessage], latest_user_input: str) -> List[BaseMessage]:
    conversation_history = [
        message for message in messages if isinstance(message, (HumanMessage, AIMessage))
    ]
    if (
        latest_user_input
        and conversation_history
        and isinstance(conversation_history[-1], HumanMessage)
        and isinstance(conversation_history[-1].content, str)
        and conversation_history[-1].content.strip() == latest_user_input
    ):
        conversation_history = conversation_history[:-1]
    return conversation_history


def _format_conversation_history(messages: List[BaseMessage]) -> str:
    if not messages:
        return "(No prior conversation.)"

    lines = []
    for message in messages:
        if isinstance(message, HumanMessage):
            role = "User"
        elif isinstance(message, AIMessage):
            role = "Assistant"
        else:
            continue

        content = message.content if isinstance(message.content, str) else str(message.content)
        lines.append(f"{role}: {content}")

    return "\n".join(lines) if lines else "(No prior conversation.)"


def _extract_active_note_updates(messages: List[BaseMessage]) -> tuple[Optional[str], Optional[str]]:
    active_note_id = None
    active_note_title = None

    for message in reversed(messages):
        if not isinstance(message, ToolMessage):
            continue
        content = message.content if isinstance(message.content, str) else str(message.content)

        note_match = NOTE_ID_RE.search(content)
        if note_match and active_note_id is None:
            active_note_id = note_match.group(1)

        title_match = TITLE_RE.search(content)
        if title_match and active_note_title is None:
            active_note_title = title_match.group(1)

        if active_note_id and active_note_title:
            break

    return active_note_id, active_note_title


def restore_session_node(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    thread_id = _extract_thread_id(config)
    if not thread_id:
        logger.info("No thread_id found in config. Skipping session restore.")
        return {}

    persisted = load_session(thread_id)
    if not persisted:
        logger.info("No persisted session found for thread_id='%s'.", thread_id)
        return {}

    incoming_messages = state.get("messages", []) or []
    restored_messages = _merge_messages(persisted.get("messages", []), incoming_messages)
    logger.info(
        "Restored persisted session for thread_id='%s' with %s message(s).",
        thread_id,
        len(restored_messages),
    )
    result: dict[str, Any] = {
        "session_messages": restored_messages,
    }

    if not state.get("active_note_id") and persisted.get("active_note_id"):
        result["active_note_id"] = persisted["active_note_id"]
    if not state.get("active_note_title") and persisted.get("active_note_title"):
        result["active_note_title"] = persisted["active_note_title"]
    return result


async def run_react_agent_node(state: AgentState) -> dict:
    logger.info("--- Node: ReAct Agent ---")

    extracted_data = state.get("extracted_data", [])
    current_messages = state.get("messages", []) or []
    session_messages = state.get("session_messages", []) or []
    messages = _merge_messages(session_messages, current_messages)
    user_input = _get_latest_user_input(messages)
    conversation_history = _get_conversation_history(messages, user_input)
    active_note_id = state.get("active_note_id")
    active_note_title = state.get("active_note_title")

    has_active_note = bool(active_note_id)
    if not extracted_data and not has_active_note:
        logger.warning("ReAct agent was called without extracted data or an active note. Ending run.")
        fallback_response = "Sorry, I don't know what content to process yet. Please provide source material or refer to an existing note."
        return {
            "messages": [AIMessage(content=fallback_response)],
        }

    task_description = (
        f"The user's original request was: '{user_input}'.\n\n"
        "Your task is to fully address this request. Pay close attention to any special instructions in the original request "
        "such as level of detail, output style, language, or whether the user wants to update an existing note.\n\n"
        f"Conversation history:\n{_format_conversation_history(conversation_history)}\n\n"
    )

    if has_active_note:
        task_description += (
            "Current active note context:\n"
            f"- active_note_id: '{active_note_id}'\n"
            f"- active_note_title: '{active_note_title or 'Unknown'}'\n"
            "If the user is referring to 'the last note', 'this note', or a follow-up edit request, prefer this note first. "
            "Use read_note before updating it when needed.\n\n"
        )

    if extracted_data:
        task_description += "Extracted content to process:\n"
        for i, item in enumerate(extracted_data):
            task_description += f"{i + 1}. Type: '{item.type}', Content: '{item.content}'\n"
    else:
        task_description += (
            "No new source material was extracted for this turn. "
            "Treat this as a follow-up request on the active note or existing saved notes.\n"
        )

    initial_agent_messages = base_prompt + conversation_history + [HumanMessage(content=task_description)]

    final_agent_state = await react_agent_graph.ainvoke(
        {"messages": initial_agent_messages},
        config={"recursion_limit": 50},
    )

    final_message = final_agent_state["messages"][-1]
    if isinstance(final_message, AIMessage):
        response_to_user = final_message.content
    else:
        response_to_user = "Agent finished processing, but the final output was a tool call."
        for msg in reversed(final_agent_state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                response_to_user = msg.content
                break

    next_active_note_id, next_active_note_title = _extract_active_note_updates(final_agent_state["messages"])
    if next_active_note_id:
        logger.info("Updated active note context to note_id='%s', title='%s'", next_active_note_id, next_active_note_title)

    logger.info(f"ReAct Agent finished. Final response: '{str(response_to_user)[:100]}...'")
    result = {
        "messages": [AIMessage(content=response_to_user)],
    }
    if next_active_note_id:
        result["active_note_id"] = next_active_note_id
    if next_active_note_title:
        result["active_note_title"] = next_active_note_title
    return result


def save_session_node(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    thread_id = _extract_thread_id(config)
    if not thread_id:
        logger.info("No thread_id found in config. Skipping session save.")
        return {}

    current_messages = state.get("messages", []) or []
    session_messages = state.get("session_messages", []) or []
    full_messages = _merge_messages(session_messages, current_messages)
    save_session(
        thread_id=thread_id,
        messages=full_messages,
        active_note_id=state.get("active_note_id"),
        active_note_title=state.get("active_note_title"),
        intent=state.get("intent"),
    )
    logger.info("Saved session for thread_id='%s' with %s message(s).", thread_id, len(full_messages))
    return {"session_messages": full_messages}


def route_after_dispatch(state: AgentState):
    intent = state.get("intent")
    if intent == "note_taking":
        logger.info("Intent 'note_taking' received. Routing to ReAct agent.")
        return "react_agent"

    logger.info(f"Intent '{intent}' received. Routing to session save and end.")
    return "save_session"


workflow = StateGraph(AgentState)
workflow.add_node("restore_session", restore_session_node)
workflow.add_node("dispatch", dispatch)
workflow.add_node("react_agent", run_react_agent_node)
workflow.add_node("save_session", save_session_node)
workflow.set_entry_point("restore_session")
workflow.add_edge("restore_session", "dispatch")
workflow.add_conditional_edges(
    "dispatch",
    route_after_dispatch,
    {
        "react_agent": "react_agent",
        "save_session": "save_session",
    },
)
workflow.add_edge("react_agent", "save_session")
workflow.add_edge("save_session", END)

graph = workflow.compile()
graph.name = "Main Coordinator Agent (ReAct Architecture)"


def get_graph(xray: bool = False):
    if xray:
        graph_to_draw = workflow.copy()
        graph_to_draw.nodes["react_agent"]["workflow"] = react_agent_graph
        return graph_to_draw
    return workflow
