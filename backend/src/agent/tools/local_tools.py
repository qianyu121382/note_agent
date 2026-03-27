"""
This module defines local tools for the agent that interact with the local filesystem or perform local computations.
"""
import json
import os
import re
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from pypdf import PdfReader

from agent.llm import llm
from agent.tools.note_store import create_note, get_note, list_notes, update_note

# --- Constants ---
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "data" / "notes"


# --- Tool Definitions ---

@tool
def read_local_document(file_path: str) -> str:
    """
    Reads content from a local document file (PDF, TXT, MD).

    Args:
        file_path: The absolute or relative path to the local file.

    Returns:
        The extracted text content of the file or an error message.
    """
    if os.path.isabs(file_path) or ".." in file_path:
        if ".." in os.path.normpath(file_path).split(os.sep):
            return "Error: Path traversal ('..') is not allowed for security reasons."

    if not os.path.exists(file_path):
        return f"Error: File not found at path: {file_path}"

    try:
        _, extension = os.path.splitext(file_path.lower())

        if extension == ".pdf":
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
            return text

        if extension in [".md", ".txt", ".py", ".js", ".html", ".css"]:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        return f"Error: Unsupported file type '{extension}'. Can only read PDF, MD, TXT, and common code files."

    except Exception as e:
        return f"Error: Failed to read or process file '{file_path}'. Reason: {e}"


_translation_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert translator. Your sole purpose is to translate the given English text into fluent, "
        "accurate, and natural-sounding Chinese. Do not add any extra commentary, analysis, or text outside "
        "of the translation itself. Preserve original formatting like Markdown and code blocks.",
    ),
    ("human", "{english_text}"),
])
_translation_chain = _translation_prompt | llm | StrOutputParser()


@tool
def translate_english_to_chinese(text: str) -> str:
    """
    Translates a given English text into Chinese. Use this tool when you encounter English content that needs to be
    processed or converted into a Chinese note.
    """
    if not isinstance(text, str) or not text.strip():
        return "Error: Input text for translation cannot be empty."

    try:
        return _translation_chain.invoke({"english_text": text})
    except Exception as e:
        return f"Error: An exception occurred during translation. Reason: {e}"


class CreateNoteInput(BaseModel):
    title: str = Field(description="Title of the note.")
    note_content: str = Field(description="The full Markdown content of the note.")
    summary: str = Field(default="", description="Short summary for indexing and listing.")
    tags: list[str] = Field(default_factory=list, description="Optional tags for the note.")
    source_type: str = Field(default="text", description="Primary source type, such as text, url, file_path, or mixed.")
    source_ref: str = Field(default="", description="Primary source reference, such as a URL or local file path.")
    thread_id: str | None = Field(default=None, description="Optional thread id associated with this note.")


@tool(args_schema=CreateNoteInput)
def create_note_record(
    title: str,
    note_content: str,
    summary: str = "",
    tags: list[str] | None = None,
    source_type: str = "text",
    source_ref: str = "",
    thread_id: str | None = None,
) -> str:
    """
    Creates a new note record consisting of a Markdown file, note metadata JSON, and an index entry.
    Use this tool when a brand-new note should be stored for later editing or retrieval.
    """
    if not note_content or not isinstance(note_content, str):
        return "Error: note_content cannot be empty."
    if not title or not isinstance(title, str):
        return "Error: title cannot be empty."

    metadata = create_note(
        title=title,
        content=note_content,
        summary=summary,
        tags=tags or [],
        source_type=source_type,
        source_ref=source_ref,
        thread_id=thread_id,
    )
    return (
        f"Successfully created note '{metadata.title}' with note_id '{metadata.note_id}'. "
        f"Markdown saved to data/notes/{metadata.filename} and metadata saved to data/notes_meta/{metadata.note_id}.json."
    )


class ReadNoteInput(BaseModel):
    note_id: str = Field(description="The unique id of the note to read.")


@tool(args_schema=ReadNoteInput)
def read_note(note_id: str) -> str:
    """
    Reads a stored note and its metadata by note_id.
    Use this tool before modifying a note or when the user asks about an existing note.
    """
    record = get_note(note_id)
    if record is None:
        return f"Error: Note with id '{note_id}' was not found."

    metadata_json = json.dumps(record.metadata.model_dump(), ensure_ascii=False, indent=2)
    return f"Metadata:\n{metadata_json}\n\nContent:\n{record.content}"


class UpdateNoteInput(BaseModel):
    note_id: str = Field(description="The unique id of the note to update.")
    note_content: str = Field(description="The full updated Markdown content of the note.")
    title: str | None = Field(default=None, description="Optional updated title.")
    summary: str | None = Field(default=None, description="Optional updated summary.")
    tags: list[str] | None = Field(default=None, description="Optional updated tags.")
    thread_id: str | None = Field(default=None, description="Optional thread id to associate with the note.")


@tool(args_schema=UpdateNoteInput)
def update_note_record(
    note_id: str,
    note_content: str,
    title: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
    thread_id: str | None = None,
) -> str:
    """
    Updates an existing stored note and bumps its metadata version.
    Use this tool when the user wants to revise, rewrite, expand, or otherwise modify an existing note.
    """
    if not note_content or not isinstance(note_content, str):
        return "Error: note_content cannot be empty."

    metadata = update_note(
        note_id,
        content=note_content,
        title=title,
        summary=summary,
        tags=tags,
        thread_id=thread_id,
        last_modified_from="edit",
    )
    if metadata is None:
        return f"Error: Note with id '{note_id}' was not found."

    return (
        f"Successfully updated note '{metadata.title}' with note_id '{metadata.note_id}'. "
        f"Current version is {metadata.version}. Markdown path: data/notes/{metadata.filename}."
    )


class ListNotesInput(BaseModel):
    limit: int = Field(default=20, description="Maximum number of notes to list.")


@tool(args_schema=ListNotesInput)
def list_note_records(limit: int = 20) -> str:
    """
    Lists stored notes from the notes index.
    Use this tool when the user asks what notes exist or when the agent needs to choose a note to modify.
    """
    notes = list_notes(limit=limit)
    if not notes:
        return "No stored notes were found."

    lines = []
    for note in notes:
        lines.append(
            f"- note_id: {note.get('note_id')} | title: {note.get('title')} | "
            f"version: {note.get('version')} | updated_at: {note.get('updated_at')}"
        )
    return "Stored notes:\n" + "\n".join(lines)


class CheckFilenameInput(BaseModel):
    filename: str = Field(description="The filename to check for existence in the project's 'data/notes' directory. Example: 'my_meeting_summary.md'")


@tool(args_schema=CheckFilenameInput)
def check_filename_exists(filename: str) -> str:
    """
    Checks if a file with the given name already exists in the project's 'data/notes' directory.
    Use this tool before manually writing a file with a fixed filename.
    """
    sane_filename = re.sub(r"[^a-zA-Z0-9_.-]", "", filename)
    if sane_filename != filename or ".." in filename or "/" in filename or "\\" in filename:
        return f"Error: Invalid filename '{filename}'. Filename should not contain paths or special characters."

    if not sane_filename.endswith(".md"):
        sane_filename += ".md"

    output_path = OUTPUT_DIR / sane_filename
    if output_path.exists():
        return f"Observation: Filename '{sane_filename}' already exists in data/notes."
    return f"Observation: Filename '{sane_filename}' is available in data/notes."


local_tools_list = [
    read_local_document,
    translate_english_to_chinese,
    create_note_record,
    read_note,
    update_note_record,
    list_note_records,
    check_filename_exists,
]



