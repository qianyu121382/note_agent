"""
Defines the main workflow for the Note Agent by wiring together subgraphs.
"""
import os
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.utils.logging import logger

# Import the subgraphs and the dispatcher node
from agent.subgraphs.dispatcher import dispatch
from agent.subgraphs.ingestion_agent import ingestion_agent_graph
from agent.subgraphs.notes_generator import notes_graph
from agent.subgraphs.deduplicator import deduplicator_graph

# --- Constants for File Output ---
OUTPUT_DIR = "output"
OUTPUT_FILENAME = "generated_note.md"

# --- Main Graph Routing Logic ---
def route_after_dispatch(state: AgentState):
    """
    After the dispatcher node, decide whether to start processing notes or end.
    """
    intent = state.get("intent")
    if intent == "note_taking":
        logger.info("Intent 'note_taking' received. Routing to ingestion agent.")
        return "ingestion_agent"
    elif intent in ["waiting", "exit"]:
        logger.info(f"Intent '{intent}' received. Ending main graph run.")
        return END
    else:
        logger.warning(f"Unknown intent: '{intent}'. Ending graph execution.")
        return END

def route_after_ingestion(state: AgentState) -> str:
    """
    After the content ingestion agent, route based on whether content was successfully parsed.
    """
    if state.get("has_successful_content"):
        logger.info("Ingestion successful. Routing to deduplicator sub-graph.")
        return "deduplicator_subgraph"
    else:
        logger.warning("Ingestion failed or produced no content. Routing back to dispatcher.")
        state["intent"] = "waiting"
        errors = state.get("processing_errors", [])
        state["response_to_user"] = "抱歉，内容处理失败：" + "".join(f"- {e}" for e in errors)
        return "dispatch"

# --- New Node for Saving File and Finalizing Response ---
def finalize_and_save_node(state: AgentState) -> dict:
    """
    Finalizes the process by saving the note and setting the final user response.
    """
    logger.info("--- Node: Finalize and Save Note ---")
    note_content = state.get("final_note")

    if not note_content or not isinstance(note_content, str):
        logger.warning("No valid note content found in 'final_note' to save. Skipping.")
        return {"response_to_user": "抱歉，笔记生成失败，没有有效内容可供保存。"}

    try:
        # Ensure the output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(note_content)

        logger.info(f"Successfully saved note to '{output_path}'")
        
        # Set the final response for the user, including the note content
        final_response = f"笔记已成功生成并保存到 `{output_path}`。\n\n---\n\n{note_content}"
        return {"response_to_user": final_response}

    except IOError as e:
        logger.error(f"Failed to write note to file: {e}", exc_info=True)
        # Handle error and inform the user
        error_message = f"错误：无法将笔记文件保存到 `{output_path}`。"
        return {"response_to_user": error_message}


# --- Main Workflow Construction ---
workflow = StateGraph(AgentState)

# 1. Add nodes (the dispatcher and the compiled subgraphs)
workflow.add_node("dispatch", dispatch)
workflow.add_node("ingestion_agent", ingestion_agent_graph)
workflow.add_node("deduplicator_subgraph", deduplicator_graph)
workflow.add_node("notes_subgraph", notes_graph)
workflow.add_node("finalize_and_save", finalize_and_save_node) # Add the new save node

# 2. Set entry point
workflow.set_entry_point("dispatch")

# 3. Build connections (edges)
workflow.add_conditional_edges(
    "dispatch",
    route_after_dispatch,
    {
        "ingestion_agent": "ingestion_agent",
        END: END,
    },
)

workflow.add_conditional_edges(
    "ingestion_agent",
    route_after_ingestion,
    {
        "deduplicator_subgraph": "deduplicator_subgraph",
        "dispatch": "dispatch", # If ingestion fails, go back to the start
    },
)

# After deduplication, always proceed to generate the note.
# The notes generator will handle whether the content is a duplicate.
workflow.add_edge("deduplicator_subgraph", "notes_subgraph")

# After generating the note, save it and finalize the response, then end.
workflow.add_edge("notes_subgraph", "finalize_and_save")
workflow.add_edge("finalize_and_save", END)

# 4. Compile the workflow
graph = workflow.compile()
graph.name = "主协调 Agent"

# --- Helper function for visualization ---
def get_graph(xray: bool = False):
    """
    Returns the uncompiled workflow object to allow for visualization.
    """
    return workflow
