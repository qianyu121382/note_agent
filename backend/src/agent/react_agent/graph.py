"""
Defines the core ReAct-style agent graph.
"""
from pathlib import Path

from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, SystemMessage

from agent.llm import llm
from agent.tools import all_tools
from agent.utils.logging import logger

# --- Agent Definition ---

# 1. Load the system prompt
prompt_path = Path(__file__).parent / "prompts" / "system.txt"
system_prompt = prompt_path.read_text(encoding="utf-8")
# The base prompt is a system message that primes the agent
base_prompt = [SystemMessage(content=system_prompt)]

# 2. Bind tools to the LLM
# This makes the LLM "tool-aware" and able to request tool calls
agent = llm.bind_tools(all_tools)

# --- Node Definitions for the Agent Graph ---

async def call_model(state: MessagesState) -> dict:
    """
    Node that calls the LLM. The LLM decides whether to respond to the user or call a tool.
    """
    logger.info("--- ReAct Agent: Calling Model ---")
    # The agent is invoked with the current message history
    response = await agent.ainvoke(state["messages"])
    # The response is a new AIMessage, possibly containing tool calls, which we add to the history
    return {"messages": [response]}

# The ToolNode is a pre-built node that executes tool calls requested by the LLM
tool_node = ToolNode(all_tools)

def should_continue(state: MessagesState) -> str:
    """
    Conditional edge logic. Decides whether to continue the loop by calling tools or to end.
    """
    last_message = state["messages"][-1]
    # If the last message is not from the AI, something is wrong
    if not isinstance(last_message, AIMessage):
        return "end"
    # If the AI message has tool calls, we route to the tool node
    if last_message.tool_calls:
        logger.info("--- ReAct Agent: Tool Call Detected. Routing to tools. ---")
        return "continue"
    # If there are no tool calls, the agent has finished its work
    logger.info("--- ReAct Agent: No Tool Call. Ending agent loop. ---")
    return "end"


# --- Graph Construction ---
react_workflow = StateGraph(MessagesState)

# Add the two nodes for the agent loop
react_workflow.add_node("call_model", call_model)
react_workflow.add_node("call_tool", tool_node)

# The entry point is the model call
react_workflow.set_entry_point("call_model")

# Define the conditional logic for the loop
react_workflow.add_conditional_edges(
    "call_model",
    should_continue,
    {
        "continue": "call_tool",
        "end": END,
    },
)

# After a tool is called, we loop back to the model to process the result
react_workflow.add_edge("call_tool", "call_model")

# Compile the graph into a runnable object
react_agent_graph = react_workflow.compile()
react_agent_graph.name = "ReAct Agent"

__all__ = ["react_agent_graph", "base_prompt"]
