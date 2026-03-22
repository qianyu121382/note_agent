"""
Defines the global state for the Note Agent.
"""
from typing import TypedDict, List, Any, Dict, Optional

# The ExtractedData schema is now part of the dispatcher subgraph
from agent.subgraphs.dispatcher.schemas import ExtractedData

class AgentState(TypedDict):
    """
    Manages the state of the Note Agent workflow.
    """
    # Initial input
    user_input: str

    # Output from the dispatcher subgraph
    intent: str
    extracted_data: Optional[List[ExtractedData]]
    response_to_user: Optional[str]

    # State for the ingestion subgraph
    urls_to_process: Optional[List[str]]
    texts_to_process: Optional[List[str]]
    parsed_url_contents: Optional[List[str]]
    parsed_text_contents: Optional[List[str]]
    all_raw_contents: Optional[str]

    # State for the notes generation process
    raw_content: str
    structured_content: str
    novel_content: str
    core_content: str
    final_note: str
    fact_check_feedback: Optional[str]
    structure_feedback: Optional[str]
    novelty_feedback: Optional[str]
    aggregated_feedback: Optional[str]
    revisions_count: int

    # State for the deduplication process
    is_duplicate: bool
    duplicate_score: Optional[float]
    existing_similar_content: Optional[str]

    # Error handling and routing
    processing_errors: Optional[List[str]]
    has_successful_content: bool
    
    # Optional fields
    input_source: str
    user_preferences: Dict[str, Any]
    generated_images: List[str]

__all__ = ["AgentState"]
