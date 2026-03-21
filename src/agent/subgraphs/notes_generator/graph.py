"""
Notes Generation Sub-Graph (Placeholder).
"""
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.utils.logging import logger

def placeholder_notes_node(state: AgentState) -> dict:
    """A placeholder node that simulates note generation."""
    logger.info("--- Sub-Graph: Notes Generation (Placeholder) ---")
    all_raw_contents = state.get("all_raw_contents", "")
    if all_raw_contents:
        # Create a simple summary as a placeholder for the final note
        final_note = f"这是根据您的内容生成的笔记摘要：{all_raw_contents[:500]}..."
        logger.info("Generated a placeholder note.")
    else:
        final_note = ""
        logger.warning("No raw content available to generate notes.")
    return {"final_note": final_note}

notes_workflow = StateGraph(AgentState)
notes_workflow.add_node("generate_notes", placeholder_notes_node)
notes_workflow.set_entry_point("generate_notes")
notes_workflow.add_edge("generate_notes", END)
notes_graph = notes_workflow.compile()
notes_graph.name = "笔记生成子图"
