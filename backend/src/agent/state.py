"""
Defines the global state for the Note Agent.
"""
from typing import Literal, Optional

from langgraph.graph import MessagesState

from agent.dispatcher.schemas import ExtractedData

AgentMode = Literal["idle", "create", "edit", "qa"]
AGENT_MODES: tuple[AgentMode, ...] = ("idle", "create", "edit", "qa")

AgentOperation = Literal[
    "none",
    "create_note",
    "locate_note",
    "general_follow_up",
    "expand_note",
    "condense_note",
    "translate_note",
    "outline_note",
    "rewrite_note",
    "summarize_note",
    "explain_note",
    "extract_points",
]
AGENT_OPERATIONS: tuple[AgentOperation, ...] = (
    "none",
    "create_note",
    "locate_note",
    "general_follow_up",
    "expand_note",
    "condense_note",
    "translate_note",
    "outline_note",
    "rewrite_note",
    "summarize_note",
    "explain_note",
    "extract_points",
)

PendingClarification = Literal["none", "note_target", "edit_operation"]
PENDING_CLARIFICATIONS: tuple[PendingClarification, ...] = (
    "none",
    "note_target",
    "edit_operation",
)


class AgentState(MessagesState):
    """
    Message-first state for the Note Agent.
    The conversation thread lives in `messages`; business routing adds a small
    amount of structured state on top.
    """

    intent: str
    mode: AgentMode
    operation: AgentOperation
    extracted_data: Optional[list[ExtractedData]]
    active_note_id: Optional[str]
    active_note_title: Optional[str]
    pending_clarification: PendingClarification
    pending_question: Optional[str]
    pending_context: Optional[dict[str, str]]


__all__ = [
    "AGENT_MODES",
    "AGENT_OPERATIONS",
    "PENDING_CLARIFICATIONS",
    "AgentMode",
    "AgentOperation",
    "PendingClarification",
    "AgentState",
]
