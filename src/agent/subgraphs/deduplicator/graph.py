"""
Deduplicator Sub-Graph.

This graph is responsible for checking if the ingested content is a duplicate
of content already present in the vector database.
"""
import os
from pathlib import Path
from langgraph.graph import StateGraph, END
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from agent.state import AgentState
from agent.utils.logging import logger

# --- Configuration ---
# Construct an absolute path to the 'db' directory to avoid CWD issues.
# The project root is 4 levels up from this file's directory.
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PERSIST_DIRECTORY = str(PROJECT_ROOT / "db")
EMBEDDING_MODEL = "text-embedding-3-small"
# NOTE: Chroma's L2 distance score is lower for more similar documents.
# A score of 0 indicates a perfect match.
# We set a low threshold to catch very similar content.
DUPLICATION_THRESHOLD = 0.15


def check_duplication_node(state: AgentState) -> dict:
    """
    Node: Checks for content duplication using the vector store.
    """
    logger.info("--- Node: Deduplication Check ---")
    
    # 1. Get content from state
    content = state.get("all_raw_contents", "").strip()
    if not content:
        logger.warning("No content provided to check for duplication. Skipping.")
        # If there's no content, it's not a duplicate, but there's nothing to process either.
        # The main graph logic will handle this. Here we just mark as not duplicate.
        return {"is_duplicate": False}

    # 2. Check if the database exists
    if not os.path.exists(PERSIST_DIRECTORY):
        logger.warning(f"Vector database not found at '{PERSIST_DIRECTORY}'. Skipping duplication check.")
        # If DB doesn't exist, nothing can be a duplicate.
        return {"is_duplicate": False}

    # 3. Load DB and perform similarity search
    try:
        logger.info("Loading existing vector database...")
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        vector_store = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            embedding_function=embeddings
        )

        logger.info("Performing similarity search...")
        results = vector_store.similarity_search_with_score(content, k=1)
        
        if not results:
            logger.info("No similar documents found in the database.")
            return {"is_duplicate": False}

        top_doc, top_score = results[0]
        logger.info(f"Most similar document found with score: {top_score:.4f}")

        # 4. Make a decision based on the threshold
        if top_score < DUPLICATION_THRESHOLD:
            logger.warning(f"Content is a potential duplicate! Score {top_score:.4f} < Threshold {DUPLICATION_THRESHOLD}")
            # Pass the duplicate info to the state for the next step to decide what to do
            return {
                "is_duplicate": True,
                "duplicate_score": top_score,
                "existing_similar_content": top_doc.page_content,
            }
        else:
            logger.info("Content is novel. Proceeding to note generation.")
            return {"is_duplicate": False, "duplicate_score": None, "existing_similar_content": None}

    except Exception as e:
        logger.error(f"An error occurred during duplication check: {e}", exc_info=True)
        # In case of error, we assume it's not a duplicate to be safe and allow processing.
        return {"is_duplicate": False, "duplicate_score": None, "existing_similar_content": None}


# --- Graph Construction ---
deduplicator_workflow = StateGraph(AgentState)
deduplicator_workflow.add_node("deduplication_check", check_duplication_node)
deduplicator_workflow.set_entry_point("deduplication_check")
deduplicator_workflow.add_edge("deduplication_check", END)

deduplicator_graph = deduplicator_workflow.compile()
deduplicator_graph.name = "内容去重子图"
