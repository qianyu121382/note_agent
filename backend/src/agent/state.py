"""
Defines the global state for the Note Agent.
"""
from typing import Optional

from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState

from agent.dispatcher.schemas import ExtractedData


class AgentState(MessagesState):
    """
    Message-first state for the Note Agent.
    The conversation thread lives in `messages`; business routing adds a small
    amount of structured state on top.
    """

    intent: str
    extracted_data: Optional[list[ExtractedData]]
    active_note_id: Optional[str]
    active_note_title: Optional[str]
    session_messages: Optional[list[BaseMessage]]


__all__ = ["AgentState"]
