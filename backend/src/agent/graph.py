"""
Defines the main workflow for the Note Agent.
The architecture is: Normalize Input -> Dispatcher -> (if needed) ReAct Agent -> Export Session -> END

When this graph runs under `langgraph dev` / LangGraph API, thread-scoped
short-term memory is managed by the platform. PostgreSQL-backed persistence is
enabled through the `POSTGRES_URI` environment variable, not through a custom
application-level checkpointer. A PostgreSQL-backed session history projection table is used by the frontend history APIs.
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
from agent.input_normalizer import normalize_input_node
from agent.react_agent.graph import base_prompt, react_agent_graph
from agent.session_state import normalize_mode, normalize_operation
from agent.session_store import export_session_snapshot
from agent.state import AgentState
from agent.utils.logging import logger

NOTE_ID_RE = re.compile(r"note_id '([^']+)'")
TITLE_RE = re.compile(r"note '([^']+)'")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _extract_thread_id(config: RunnableConfig | None) -> Optional[str]:
    if not config:
        return None
    configurable = config.get("configurable", {})
    if not isinstance(configurable, dict):
        return None
    thread_id = configurable.get("thread_id")
    return str(thread_id) if thread_id else None


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


def _stringify_content_part(part: Any) -> str:
    if isinstance(part, str):
        return part
    if not isinstance(part, dict):
        return str(part)

    part_type = part.get("type")
    if part_type == "text":
        return str(part.get("text", ""))
    if part_type == "image":
        metadata = part.get("metadata") if isinstance(part.get("metadata"), dict) else {}
        name = str(metadata.get("name") or "")
        return f"[Attached image{name and f': {name}' or ''}]"
    if part_type == "file":
        metadata = part.get("metadata") if isinstance(part.get("metadata"), dict) else {}
        filename = str(metadata.get("filename") or metadata.get("name") or "")
        mime_type = str(part.get("mimeType") or "file")
        label = filename or mime_type
        return f"[Attached file: {label}]"
    return str(part)


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [_stringify_content_part(part).strip() for part in content]
        return "\n".join(part for part in parts if part)
    return str(content)


def _sanitize_message_for_model(message: BaseMessage) -> BaseMessage:
    text_content = _content_to_text(message.content).strip() or "(empty message)"
    if isinstance(message, HumanMessage):
        return HumanMessage(content=text_content)
    if isinstance(message, AIMessage):
        return AIMessage(content=text_content)
    return message


def _sanitize_conversation_history(messages: List[BaseMessage]) -> List[BaseMessage]:
    return [
        _sanitize_message_for_model(message)
        for message in messages
        if isinstance(message, (HumanMessage, AIMessage))
    ]


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

        content = _content_to_text(message.content)
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


def _prefers_chinese(text: str) -> bool:
    return bool(CJK_RE.search(text or ""))


def _build_missing_context_response(user_input: str) -> str:
    if _prefers_chinese(user_input):
        return "我目前还不知道你要处理哪一篇笔记。请提供原始资料，或者明确说明要修改哪篇已有笔记。"
    return (
        "I don't know which note you want to work on yet. "
        "Please provide source material or specify which existing note you want to modify."
    )


def _can_proceed_without_active_note(extracted_data: list[Any], operation: str) -> bool:
    return bool(extracted_data) or operation == "locate_note"


async def run_react_agent_node(state: AgentState) -> dict[str, Any]:
    logger.info("--- Node: ReAct Agent ---")

    messages = state.get("messages", []) or []
    extracted_data = state.get("extracted_data", []) or []
    user_input = _get_latest_user_input(messages)
    conversation_history = _sanitize_conversation_history(
        _get_conversation_history(messages, user_input)
    )
    active_note_id = state.get("active_note_id")
    active_note_title = state.get("active_note_title")
    mode = normalize_mode(state.get("mode"))
    operation = normalize_operation(state.get("operation"))

    if not _can_proceed_without_active_note(extracted_data, operation) and not active_note_id:
        logger.warning("ReAct agent was called without extracted data or an active note. Ending run.")
        fallback_response = _build_missing_context_response(user_input)
        return {
            "messages": [AIMessage(content=fallback_response)],
            "mode": mode,
            "operation": operation,
        }

    task_description = (
        f"Current session mode: '{mode}'.\n"
        f"Current session operation: '{operation}'.\n"
        f"The user's original request was: '{user_input}'.\n\n"
        "Your task is to fully address this request. Pay close attention to any special instructions in the original request "
        "such as level of detail, output style, language, or whether the user wants to update an existing note.\n\n"
        f"Conversation history:\n{_format_conversation_history(conversation_history)}\n\n"
    )

    if mode == "create":
        task_description += (
            "The current session is in create mode. Treat new extracted source material as the primary input and create a new note when appropriate.\n\n"
        )
    elif mode == "edit":
        task_description += (
            "The current session is in edit mode. Prefer updating the active note rather than creating a new one. Read the note before modifying it when needed.\n\n"
        )
    elif mode == "qa":
        task_description += (
            "The current session is in QA mode. Prefer answering based on the active note instead of editing its body unless the user explicitly asks for a revision.\n\n"
        )

    if operation != "none":
        task_description += (
            f"The finer-grained requested operation is '{operation}'. Respect it when choosing tools and shaping the final output.\n\n"
        )

    if operation == "locate_note":
        task_description += (
            "The current task first requires locating an existing note. Use the locate_note skill and note search/list tools before attempting any edit or QA action.\n\n"
        )

    if active_note_id:
        task_description += (
            "Current active note context:\n"
            f"- active_note_id: '{active_note_id}'\n"
            f"- active_note_title: '{active_note_title or 'Unknown'}'\n"
            "If the user is referring to 'the last note', 'this note', or a follow-up request, prefer this note first. "
            "Use read_note before updating it when needed.\n\n"
        )

    if extracted_data:
        task_description += "Extracted content to process:\n"
        for i, item in enumerate(extracted_data):
            task_description += f"{i + 1}. Type: '{item.type}', Content: '{item.content}'\n"
    else:
        task_description += (
            "No new source material was extracted for this turn. "
            "Treat this as a follow-up request on the active note or on existing saved notes that may need to be located first.\n"
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
        logger.info(
            "Updated active note context to note_id='%s', title='%s'",
            next_active_note_id,
            next_active_note_title,
        )

    logger.info(f"ReAct Agent finished. Final response: '{str(response_to_user)[:100]}...'")
    result: dict[str, Any] = {
        "messages": [AIMessage(content=response_to_user)],
        "mode": mode,
        "operation": operation,
    }
    if next_active_note_id:
        result["active_note_id"] = next_active_note_id
    if next_active_note_title:
        result["active_note_title"] = next_active_note_title
    return result


def export_session_node(state: AgentState, config: RunnableConfig | None = None) -> dict[str, Any]:
    thread_id = _extract_thread_id(config)
    if not thread_id:
        logger.info("No thread_id found in config. Skipping session export.")
        return {}

    messages = state.get("messages", []) or []
    export_session_snapshot(
        thread_id=thread_id,
        messages=messages,
        active_note_id=state.get("active_note_id"),
        active_note_title=state.get("active_note_title"),
        intent=state.get("intent"),
        mode=normalize_mode(state.get("mode")),
        operation=normalize_operation(state.get("operation")),
    )
    logger.info("Exported session snapshot for thread_id='%s' with %s message(s).", thread_id, len(messages))
    return {}


def route_after_dispatch(state: AgentState):
    intent = state.get("intent")
    if intent == "note_taking":
        logger.info("Intent 'note_taking' received. Routing to ReAct agent.")
        return "react_agent"

    logger.info(f"Intent '{intent}' received. Routing to session export and end.")
    return "export_session"


workflow = StateGraph(AgentState)
workflow.add_node("normalize_input", normalize_input_node)
workflow.add_node("dispatch", dispatch)
workflow.add_node("react_agent", run_react_agent_node)
workflow.add_node("export_session", export_session_node)
workflow.set_entry_point("normalize_input")
workflow.add_edge("normalize_input", "dispatch")
workflow.add_conditional_edges(
    "dispatch",
    route_after_dispatch,
    {
        "react_agent": "react_agent",
        "export_session": "export_session",
    },
)
workflow.add_edge("react_agent", "export_session")
workflow.add_edge("export_session", END)

graph = workflow.compile()
graph.name = "Main Coordinator Agent (ReAct Architecture)"


def get_graph(xray: bool = False):
    if xray:
        graph_to_draw = workflow.copy()
        graph_to_draw.nodes["react_agent"]["workflow"] = react_agent_graph
        return graph_to_draw
    return workflow
