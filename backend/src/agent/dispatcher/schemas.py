"""
Defines the structured output models used by the dispatcher node.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ExtractedData(BaseModel):
    """Structured content extracted from the latest user input."""

    type: Literal["url", "text", "file_path"] = Field(
        description="The extracted data type: url, text, or file_path."
    )
    content: str = Field(
        description="The cleaned content value, such as the URL, text body, or local file path."
    )


class DispatcherOutput(BaseModel):
    """Structured dispatcher output for routing and operation-level intent."""

    intent: Literal["note_taking", "waiting", "exit"] = Field(
        description=(
            "The top-level routing result. note_taking means the request should enter the note-processing chain; "
            "waiting means the input is incomplete or out of scope; exit means the user wants to stop."
        )
    )
    operation: Optional[
        Literal[
            "none",
            "create_note",
            "locate_note",
            "general_follow_up",
            "expand_note",
            "condense_note",
            "translate_note",
            "outline_note",
            "rewrite_note",
            "summarize_note",
            "explain_note",
            "extract_points",
        ]
    ] = Field(
        default=None,
        description=(
            "A finer-grained operation label for note_taking requests. "
            "Use create_note for new material; use locate_note when the user is clearly referring to an existing note "
            "but the target note still needs to be located; use edit-style operations such as expand_note / condense_note / "
            "translate_note / outline_note / rewrite_note for note revisions; use summarize_note / explain_note / "
            "extract_points for note-based QA. Use general_follow_up when the request is clearly a follow-up but the "
            "specific operation is not obvious. Use none for waiting or exit."
        ),
    )
    data: Optional[List[ExtractedData]] = Field(
        description=(
            "A list of extracted input data items. When note_taking is triggered by newly provided material, this should "
            "contain the cleaned source items."
        )
    )
    response_to_user: Optional[str] = Field(
        default=None,
        description=(
            "When intent is waiting, provide a short, natural reply that explains why the request cannot be processed yet "
            "and guides the user toward providing usable input."
        ),
    )
