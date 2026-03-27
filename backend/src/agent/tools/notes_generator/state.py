"""
Defines the internal state for the Notes Generator tool's graph.
"""
from typing import TypedDict, Optional

class NotesGeneratorState(TypedDict):
    """
    A local state for the notes generator graph to manage its internal process.
    """
    raw_content: str
    final_note: str
    fact_check_feedback: Optional[str]
    structure_feedback: Optional[str]
    novelty_feedback: Optional[str]
    aggregated_feedback: Optional[str]
    revisions_count: int
