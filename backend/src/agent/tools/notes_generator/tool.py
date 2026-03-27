"""
Defines the final, agent-facing tool that wraps the internal notes generator graph.
"""
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from agent.utils.logging import logger
from .graph import notes_graph
from .state import NotesGeneratorState

# --- Tool Definition ---
class NotesGeneratorToolInput(BaseModel):
    """Input schema for the notes generator tool."""
    raw_content: str = Field(description="The raw, unstructured text content that needs to be refined and organized into a note.")

@tool(args_schema=NotesGeneratorToolInput)
def refine_and_generate_note(raw_content: str) -> str:
    """
    Use this tool to process, refine, and structure raw text into a high-quality, well-formatted Markdown note.
    It internally uses a multi-agent debate process for drafting, reviewing, and revising to improve quality.
    This is ideal for turning a block of text into a clear, concise, and organized summary.
    """
    logger.info("--- Tool: refine_and_generate_note invoked ---")
    
    # Prepare the initial state for the internal graph
    initial_state: NotesGeneratorState = {
        "raw_content": raw_content,
        "final_note": "",
        "revisions_count": 0,
        "aggregated_feedback": "",
        "fact_check_feedback": "",
        "structure_feedback": "",
        "novelty_feedback": "",
    }

    # Invoke the internal graph and get the final state
    final_state = notes_graph.invoke(initial_state)
    generated_note = final_state.get("final_note")

    if not generated_note or not isinstance(generated_note, str):
        return "Error: The note generation process failed to produce valid content."

    return generated_note
