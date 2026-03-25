"""
Defines the global state for the Note Agent.
"""
import operator
from typing import TypedDict, List, Annotated, Optional
from langchain_core.messages import BaseMessage
from agent.dispatcher.schemas import ExtractedData

class AgentState(TypedDict):
    """
    Manages the state of the new Agent workflow.
    This state is passed between the dispatcher and the main ReAct agent.
    """
    # Input from the user
    user_input: str

    # Output from the dispatcher node
    intent: str
    extracted_data: Optional[List[ExtractedData]]

    # The 'messages' field is the core of the ReAct agent's memory.
    # It's a list of messages that grows with each step of the agent's thought process.
    # `operator.add` ensures that new messages are appended to the list rather than replacing it.
    messages: Annotated[List[BaseMessage], operator.add]

    # The final response to be shown to the user.
    response_to_user: Optional[str]

__all__ = ["AgentState"]
