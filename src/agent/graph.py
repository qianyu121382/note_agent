"""
Defines the main, simplified workflow for the Note Agent.
The new architecture is: Dispatcher -> (if note_taking) -> ReAct Agent -> END
"""
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from agent.state import AgentState
from agent.utils.logging import logger
from agent.dispatcher import dispatch
from agent.react_agent.graph import react_agent_graph, base_prompt


async def run_react_agent_node(state: AgentState) -> dict:
    """
    This node runs the entire ReAct agent sub-graph.
    It prepares the initial input for the agent and processes its final output.
    """
    logger.info("--- Node: ReAct Agent ---")
    
    # 1. Prepare the initial message for the agent based on dispatcher output
    extracted_data = state.get("extracted_data", [])
    user_input = state.get("user_input", "")

    if not extracted_data:
        # This should ideally not happen if routing is correct, but as a safeguard:
        logger.warning("ReAct agent was called but no data was extracted. Ending run.")
        return {"response_to_user": "抱歉，我不知道要处理什么内容。"}

    # Format the initial user request for the agent, now including the original input
    task_description = (
        f"The user's original request was: '{user_input}'.\n\n"
        "Your task is to fully address this request by processing the following extracted content. "
        "Pay close attention to any special instructions in the original request (e.g., 'make it detailed', 'summarize briefly').\n\n"
        "Extracted content to process:\n"
    )
    for i, item in enumerate(extracted_data):
        task_description += f"{i+1}. Type: '{item.type}', Content: '{item.content}'\n"
    
    # The initial state for the ReAct agent includes the system prompt and the formatted task
    initial_agent_messages = base_prompt + [HumanMessage(content=task_description)]
    
    # 2. Invoke the ReAct agent graph
    final_agent_state = await react_agent_graph.ainvoke(
        {"messages": initial_agent_messages},
        # Add a high recursion limit to allow for complex multi-step tasks
        config={"recursion_limit": 50}
    )
    
    # 3. Extract the final response from the agent's message history
    final_message = final_agent_state["messages"][-1]
    if isinstance(final_message, AIMessage):
        response_to_user = final_message.content
    else:
        # If the last message is not from the AI, it's likely a tool output.
        # This indicates the agent may have ended prematurely. We find the last AI message.
        response_to_user = "Agent finished processing, but the final output was a tool call."
        for msg in reversed(final_agent_state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                response_to_user = msg.content
                break
    
    logger.info(f"ReAct Agent finished. Final response: '{response_to_user[:100]}...'")
    return {"response_to_user": response_to_user}


def route_after_dispatch(state: AgentState):
    """
    After the dispatcher node, decide whether to start the ReAct agent or end.
    """
    intent = state.get("intent")
    if intent == "note_taking":
        logger.info("Intent 'note_taking' received. Routing to ReAct agent.")
        return "react_agent"
    
    logger.info(f"Intent '{intent}' received. Ending main graph run.")
    # For "waiting" or "exit", the dispatcher already set the response_to_user.
    # We can end the graph here.
    return END

# --- Main Workflow Construction ---
workflow = StateGraph(AgentState)

# 1. Add nodes
workflow.add_node("dispatch", dispatch)
workflow.add_node("react_agent", run_react_agent_node)

# 2. Set entry point
workflow.set_entry_point("dispatch")

# 3. Build connections (edges)
workflow.add_conditional_edges(
    "dispatch",
    route_after_dispatch,
    {
        "react_agent": "react_agent",
        END: END,
    },
)

# After the agent runs, the process is complete.
workflow.add_edge("react_agent", END)

# 4. Compile the workflow
graph = workflow.compile()
graph.name = "主协调 Agent (ReAct 架构)"

# --- Helper function for visualization ---
def get_graph(xray: bool = False):
    """
    Returns the uncompiled workflow object to allow for visualization.
    If xray is true, it will try to show the sub-graph details.
    """
    if xray:
        # To visualize the react_agent_graph inside, we can substitute it
        # This is a bit of a hack for visualization purposes
        graph_to_draw = workflow.copy()
        graph_to_draw.nodes["react_agent"]['workflow'] = react_agent_graph
        return graph_to_draw
    return workflow
