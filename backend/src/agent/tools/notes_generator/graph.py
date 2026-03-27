"""
Defines the internal graph for the multi-agent debate and revision process.
"""
from langgraph.graph import StateGraph, END
from agent.utils.logging import logger
from .state import NotesGeneratorState
from .prompts import (
    draft_chain,
    fact_checker_chain,
    structure_reviewer_chain,
    novelty_reviewer_chain,
    revise_chain,
)

# --- Constants ---
MAX_REVISIONS = 2
FACTS_OK_KEYWORD = "[FACTS_OK]"
STRUCTURE_OK_KEYWORD = "[STRUCTURE_OK]"
CONCISENESS_OK_KEYWORD = "[CONCISENESS_OK]"


# --- Node Definitions ---
def initial_draft_node(state: NotesGeneratorState) -> dict:
    logger.info("--- (Inner) Node: Generate Initial Draft ---")
    raw_content = state.get("raw_content", "").strip()
    if not raw_content:
        return {"final_note": ""}

    # Simplified: no longer checks for existing content
    final_note = draft_chain.invoke({
        "raw_content": raw_content,
        "existing_content_section": ""
    })
    return {"final_note": final_note, "revisions_count": 0}

def fact_check_node(state: NotesGeneratorState) -> dict:
    feedback = fact_checker_chain.invoke({"raw_content": state["raw_content"], "draft": state["final_note"]})
    return {"fact_check_feedback": feedback}

def structure_review_node(state: NotesGeneratorState) -> dict:
    feedback = structure_reviewer_chain.invoke({"raw_content": state["raw_content"], "draft": state["final_note"]})
    return {"structure_feedback": feedback}

def novelty_review_node(state: NotesGeneratorState) -> dict:
    feedback = novelty_reviewer_chain.invoke({"raw_content": state["raw_content"], "draft": state["final_note"]})
    return {"novelty_feedback": feedback}

def aggregate_feedback_node(state: NotesGeneratorState) -> dict:
    feedbacks = {
        "事实核查员": state.get("fact_check_feedback"),
        "结构与格式评审员": state.get("structure_feedback"),
        "简洁度评审员": state.get("novelty_feedback"),
    }
    aggregated_str = ""
    for reviewer, feedback in feedbacks.items():
        if feedback and not any(ok in feedback for ok in [FACTS_OK_KEYWORD, STRUCTURE_OK_KEYWORD, CONCISENESS_OK_KEYWORD]):
            aggregated_str += f"### 来自“{reviewer}”的意见:\n{feedback}\n\n"
    return {"aggregated_feedback": aggregated_str.strip()}

def revise_note_node(state: NotesGeneratorState) -> dict:
    revisions_count = state.get("revisions_count", 0) + 1
    revised_note = revise_chain.invoke({
        "raw_content": state["raw_content"],
        "draft": state["final_note"],
        "feedback": state["aggregated_feedback"]
    })
    return {"final_note": revised_note, "revisions_count": revisions_count}

def decide_after_review(state: NotesGeneratorState) -> str:
    revisions_count = state.get("revisions_count", 0)
    aggregated_feedback = state.get("aggregated_feedback", "")

    if not aggregated_feedback:
        logger.info("All reviewers approved. Ending revision loop.")
        return "end"
        
    if revisions_count >= MAX_REVISIONS:
        logger.warning(f"Max revisions ({MAX_REVISIONS}) reached. Ending revision loop.")
        return "end"
        
    logger.info("Reviewer(s) provided feedback. Routing to revision node.")
    return "revise"


# --- Graph Construction ---
notes_workflow = StateGraph(NotesGeneratorState)
notes_workflow.add_node("draft", initial_draft_node)
notes_workflow.add_node("fact_check", fact_check_node)
notes_workflow.add_node("structure_review", structure_review_node)
notes_workflow.add_node("novelty_review", novelty_review_node)
notes_workflow.add_node("aggregate_feedback", aggregate_feedback_node)
notes_workflow.add_node("revise", revise_note_node)

notes_workflow.set_entry_point("draft")
notes_workflow.add_edge("draft", "fact_check")
notes_workflow.add_edge("draft", "structure_review")
notes_workflow.add_edge("draft", "novelty_review")
notes_workflow.add_edge("fact_check", "aggregate_feedback")
notes_workflow.add_edge("structure_review", "aggregate_feedback")
notes_workflow.add_edge("novelty_review", "aggregate_feedback")
notes_workflow.add_conditional_edges("aggregate_feedback", decide_after_review, {"revise": "revise", "end": END})
# After revising, loop back for another round of critique
notes_workflow.add_edge("revise", "fact_check")
notes_workflow.add_edge("revise", "structure_review")
notes_workflow.add_edge("revise", "novelty_review")

# Compile the graph
notes_graph = notes_workflow.compile()
notes_graph.name = "笔记生成子图（多视角反思）"
