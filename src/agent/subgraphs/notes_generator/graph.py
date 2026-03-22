"""
Notes Generation Sub-Graph with Multi-Perspective Reflection.

This subgraph implements a "Multi-Agent-Debate" style pattern to improve
the quality of the generated notes. The process is as follows:
1.  DRAFT: Generate an initial note.
2.  PARALLEL REVIEW: Three specialist agents critique the draft simultaneously:
    - Fact-Checker: Checks for factual accuracy against the source.
    - Structure & Formatting Reviewer: Checks for clarity and proper Markdown.
    - Novelty & Conciseness Reviewer: Checks for redundancy and adherence to
      the "no-duplication" rule.
3.  AGGREGATE: Collect all feedback.
4.  REVISE: A single optimizer agent revises the draft based on the
    aggregated feedback.
"""
from pathlib import Path
from typing import List
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser

from agent.state import AgentState
from agent.utils.logging import logger
from agent.llm import llm

# --- Constants ---
MAX_REVISIONS = 3
# Approval keywords for each reviewer
FACTS_OK_KEYWORD = "[FACTS_OK]"
STRUCTURE_OK_KEYWORD = "[STRUCTURE_OK]"
NOVELTY_OK_KEYWORD = "[NOVELTY_OK]"


# --- Prompt and Chain Definitions ---

def create_prompt_from_file(filename: str, human_template: str) -> ChatPromptTemplate:
    """Helper to create a ChatPromptTemplate from a system prompt file."""
    try:
        prompt_path = Path(__file__).parent / "prompts" / filename
        system_prompt = SystemMessagePromptTemplate.from_template(prompt_path.read_text(encoding="utf-8"))
        human_prompt = HumanMessagePromptTemplate.from_template(human_template)
        return ChatPromptTemplate.from_messages([system_prompt, human_prompt])
    except Exception as e:
        logger.error(f"Failed to create prompt from '{filename}': {e}", exc_info=True)
        raise

# 1. Initial Draft Generator
draft_human_template = (
    "{existing_content_section}"
    "这是需要你整理和总结的原始文本，请开始处理：\n\n---\n\n{raw_content}"
)
draft_prompt = create_prompt_from_file("system.txt", draft_human_template)
draft_chain = draft_prompt | llm | StrOutputParser()

# 2. Reviewer Chains
review_human_template = (
    "原始文本:\n---\n{raw_content}\n---\n\n"
    "待评审的笔记草稿:\n---\n{draft}\n---"
)
fact_checker_prompt = create_prompt_from_file("fact_checker_system.txt", review_human_template)
fact_checker_chain = fact_checker_prompt | llm | StrOutputParser()

structure_reviewer_prompt = create_prompt_from_file("structure_reviewer_system.txt", review_human_template)
structure_reviewer_chain = structure_reviewer_prompt | llm | StrOutputParser()

novelty_reviewer_prompt = create_prompt_from_file("novelty_reviewer_system.txt", review_human_template)
novelty_reviewer_chain = novelty_reviewer_prompt | llm | StrOutputParser()

# 3. Optimizer/Reviser Chain
revise_human_template = (
    "原始文本:\n---\n{raw_content}\n---\n\n"
    "上一版笔记草稿:\n---\n{draft}\n---\n\n"
    "评审委员会的综合修改意见:\n---\n{feedback}\n---"
)
revise_prompt = create_prompt_from_file("optimizer_system.txt", revise_human_template)
revise_chain = revise_prompt | llm | StrOutputParser()


# --- Node Definitions ---

def initial_draft_node(state: AgentState) -> dict:
    """Node: Generates the initial draft of the note."""
    logger.info("--- Node: Generate Initial Draft ---")
    state["revisions_count"] = 0
    all_raw_contents = state.get("all_raw_contents", "").strip()
    is_duplicate = state.get("is_duplicate", False)
    existing_similar_content = state.get("existing_similar_content")

    if not all_raw_contents:
        logger.warning("No raw content. Skipping note generation.")
        return {"final_note": "", "all_raw_contents": ""}

    existing_content_section = ""
    if is_duplicate and existing_similar_content:
        logger.info("Similar content found, creating contextual prompt for LLM.")
        existing_content_section = (
            f"[EXISTING_CONTENT]\n{existing_similar_content}\n[/EXISTING_CONTENT]\n\n"
        )
    
    logger.info("Invoking LLM to generate initial draft...")
    final_note = draft_chain.invoke({
        "raw_content": all_raw_contents,
        "existing_content_section": existing_content_section
    })
    logger.info("Successfully generated initial draft.")
    return {"final_note": final_note, "revisions_count": 0}

# --- Parallel Reviewer Nodes ---
def fact_check_node(state: AgentState) -> dict:
    """Node: Runs the fact-checker reviewer."""
    logger.info("--- Reviewer: Fact-Checker ---")
    feedback = fact_checker_chain.invoke({
        "raw_content": state["all_raw_contents"], "draft": state["final_note"]
    })
    logger.info(f"Fact-Checker Feedback: {feedback.strip()}")
    return {"fact_check_feedback": feedback}

def structure_review_node(state: AgentState) -> dict:
    """Node: Runs the structure & formatting reviewer."""
    logger.info("--- Reviewer: Structure & Formatting ---")
    feedback = structure_reviewer_chain.invoke({
        "raw_content": state["all_raw_contents"], "draft": state["final_note"]
    })
    logger.info(f"Structure Feedback: {feedback.strip()}")
    return {"structure_feedback": feedback}

def novelty_review_node(state: AgentState) -> dict:
    """Node: Runs the novelty & conciseness reviewer."""
    logger.info("--- Reviewer: Novelty & Conciseness ---")
    feedback = novelty_reviewer_chain.invoke({
        "raw_content": state["all_raw_contents"], "draft": state["final_note"]
    })
    logger.info(f"Novelty Feedback: {feedback.strip()}")
    return {"novelty_feedback": feedback}

# --- Aggregator and Reviser Nodes ---
def aggregate_feedback_node(state: AgentState) -> dict:
    """Node: Collects all feedback and formats it for the optimizer."""
    logger.info("--- Node: Aggregate Feedback ---")
    
    feedbacks = {
        "事实核查员": state.get("fact_check_feedback"),
        "结构与格式评审员": state.get("structure_feedback"),
        "新颖性与简洁度评审员": state.get("novelty_feedback"),
    }
    
    aggregated_str = ""
    for reviewer, feedback in feedbacks.items():
        if feedback and not any(ok in feedback for ok in [FACTS_OK_KEYWORD, STRUCTURE_OK_KEYWORD, NOVELTY_OK_KEYWORD]):
            aggregated_str += f"### 来自“{reviewer}”的意见:\n{feedback}\n\n"
    
    if not aggregated_str:
        logger.info("All reviewers approved. No feedback to aggregate.")
        return {"aggregated_feedback": ""}
        
    logger.info(f"Aggregated feedback for optimizer:\n{aggregated_str}")
    return {"aggregated_feedback": aggregated_str.strip()}


def revise_note_node(state: AgentState) -> dict:
    """Node: Revises the note based on aggregated feedback."""
    logger.info("--- Node: Revise Note ---")
    revisions_count = state.get("revisions_count", 0) + 1
    state["revisions_count"] = revisions_count
    logger.info(f"Revision attempt: {revisions_count}")

    revised_note = revise_chain.invoke({
        "raw_content": state["all_raw_contents"],
        "draft": state["final_note"],
        "feedback": state["aggregated_feedback"]
    })
    logger.info("Successfully revised note.")
    return {"final_note": revised_note, "revisions_count": revisions_count}


# --- Conditional Routing ---
def decide_after_review(state: AgentState) -> str:
    """Router: Checks all review feedbacks to decide the next step."""
    logger.info("--- Router: Decide After Review ---")
    revisions_count = state.get("revisions_count", 0)
    
    fact_feedback = state.get("fact_check_feedback", "")
    structure_feedback = state.get("structure_feedback", "")
    novelty_feedback = state.get("novelty_feedback", "")
    
    all_ok = (FACTS_OK_KEYWORD in fact_feedback and 
              STRUCTURE_OK_KEYWORD in structure_feedback and 
              NOVELTY_OK_KEYWORD in novelty_feedback)

    if all_ok:
        logger.info("All reviewers approved the draft. Ending process.")
        return "end"
    
    if revisions_count >= MAX_REVISIONS:
        logger.warning(f"Max revisions ({MAX_REVISIONS}) reached. Ending process.")
        return "end"
        
    logger.info("Reviewer(s) provided feedback. Routing to revision node.")
    return "revise"


# --- Graph Construction ---
notes_workflow = StateGraph(AgentState)

notes_workflow.add_node("draft", initial_draft_node)
# Parallel review nodes
notes_workflow.add_node("fact_check", fact_check_node)
notes_workflow.add_node("structure_review", structure_review_node)
notes_workflow.add_node("novelty_review", novelty_review_node)
# Aggregator and reviser nodes
notes_workflow.add_node("aggregate_feedback", aggregate_feedback_node)
notes_workflow.add_node("revise", revise_note_node)

# --- Edge Definitions ---
notes_workflow.set_entry_point("draft")
# From draft to all reviewers for parallel execution
notes_workflow.add_edge("draft", "fact_check")
notes_workflow.add_edge("draft", "structure_review")
notes_workflow.add_edge("draft", "novelty_review")

# Reviewers all connect to the aggregator
notes_workflow.add_edge("fact_check", "aggregate_feedback")
notes_workflow.add_edge("structure_review", "aggregate_feedback")
notes_workflow.add_edge("novelty_review", "aggregate_feedback")

# From aggregator, make a decision
notes_workflow.add_conditional_edges(
    "aggregate_feedback",
    decide_after_review,
    {"revise": "revise", "end": END}
)
# After revising, loop back to the reviewers for another round of critique.
notes_workflow.add_edge("revise", "fact_check")
notes_workflow.add_edge("revise", "structure_review")
notes_workflow.add_edge("revise", "novelty_review")

# Compile the graph
notes_graph = notes_workflow.compile()
notes_graph.name = "笔记生成子图（多视角反思）"
