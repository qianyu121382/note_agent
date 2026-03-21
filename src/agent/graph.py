"""
Defines the main workflow for the Note Agent by wiring together subgraphs.
"""
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.utils.logging import logger

# Import the subgraphs and the dispatcher node
from agent.subgraphs.dispatcher import dispatch
from agent.subgraphs.ingestion import ingestion_graph
from agent.subgraphs.notes_generator import notes_graph

# --- Main Graph Routing Logic ---
def route_after_dispatch(state: AgentState):
    """
    After the dispatcher node, decide whether to start processing notes or end.
    """
    intent = state.get("intent")
    if intent == "note_taking":
        logger.info("Intent 'note_taking' received. Routing to ingestion sub-graph.")
        return "ingestion_subgraph"
    elif intent in ["waiting", "exit"]:
        logger.info(f"Intent '{intent}' received. Ending main graph run.")
        return END
    else:
        logger.warning(f"Unknown intent: '{intent}'. Ending graph execution.")
        return END

def route_after_ingestion(state: AgentState) -> str:
    """
    After the content ingestion sub-graph, route based on whether content was successfully parsed.
    """
    if state.get("has_successful_content"):
        logger.info("Ingestion successful. Routing to notes generation sub-graph.")
        return "notes_subgraph"
    else:
        logger.warning("Ingestion failed or produced no content. Routing back to dispatcher.")
        state["intent"] = "waiting" 
        errors = state.get("processing_errors", [])
        state["response_to_user"] = "抱歉，内容处理失败：" + "".join(f"- {e}" for e in errors)
        return "dispatch"

# --- Main Workflow Construction ---
workflow = StateGraph(AgentState)

# 1. Add nodes (the dispatcher and the compiled subgraphs)
workflow.add_node("dispatch", dispatch)
workflow.add_node("ingestion_subgraph", ingestion_graph)
workflow.add_node("notes_subgraph", notes_graph)

# 2. Set entry point
workflow.set_entry_point("dispatch")

# 3. Build connections (edges)
workflow.add_conditional_edges(
    "dispatch",
    route_after_dispatch,
    {
        "ingestion_subgraph": "ingestion_subgraph",
        END: END,
    },
)

workflow.add_conditional_edges(
    "ingestion_subgraph",
    route_after_ingestion,
    {
        "notes_subgraph": "notes_subgraph",
        "dispatch": "dispatch", # If ingestion fails, go back to the start
    },
)

workflow.add_edge("notes_subgraph", END)

# 4. Compile the workflow
graph = workflow.compile()
graph.name = "主协调 Agent"

# --- Helper function for visualization ---
def get_graph(xray: bool = False):
    """
    Returns the uncompiled workflow object to allow for visualization.
    """
    return workflow
