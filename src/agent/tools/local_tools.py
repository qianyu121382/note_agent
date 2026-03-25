"""
This module defines local tools for the agent that interact with the local filesystem or perform local computations.
"""
import os
import re
from pathlib import Path
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from pypdf import PdfReader

# Import shared LLM and necessary components for the new tool
from agent.llm import llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agent.utils.logging import logger

# --- Constants ---
OUTPUT_DIR = "output"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
    # Security check: Ensure the path is within the project or a designated safe directory.
    # This is a basic example; a production system would need more robust sandboxing.
    # For now, let's just check if the path is not absolute and doesn't try to go up too many levels.
    if os.path.isabs(file_path) or ".." in file_path:
         # For simplicity in this project, we allow relative paths but restrict ".."
         # A real-world scenario would need a more sophisticated allow-list of directories.
         if ".." in os.path.normpath(file_path).split(os.sep):
              return f"Error: Path traversal ('..') is not allowed for security reasons."

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
                    text += page_text + ""
            return text
        
        elif extension in [".md", ".txt", ".py", ".js", ".html", ".css"]:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        
        else:
            return f"Error: Unsupported file type '{extension}'. Can only read PDF, MD, TXT, and common code files."

    except Exception as e:
        return f"Error: Failed to read or process file '{file_path}'. Reason: {e}"


# --- New Translation Tool ---
_translation_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert translator. Your sole purpose is to translate the given English text into fluent, "
               "accurate, and natural-sounding Chinese. Do not add any extra commentary, analysis, or text outside "
               "of the translation itself. Preserve original formatting like Markdown and code blocks."),
    ("human", "{english_text}")
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


# --- New Save Note Tool ---
class SaveNoteInput(BaseModel):
    filename: str = Field(description="The desired filename for the note, including the .md extension. Example: 'my_meeting_summary.md'")
    note_content: str = Field(description="The full Markdown content of the note to be saved.")

@tool(args_schema=SaveNoteInput)
def save_note(filename: str, note_content: str) -> str:
    """
    Saves the provided content to a specified Markdown file in the './output' directory.
    Use this tool after a note has been fully generated and is ready to be stored.
    The agent is responsible for creating a descriptive and valid filename.
    """
    sane_filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
    if sane_filename != filename or ".." in filename or "/" in filename or "\\" in filename:
        return f"Error: Invalid filename '{filename}'. Filename should not contain paths or special characters."
    
    if not sane_filename.endswith(".md"):
        sane_filename += ".md"

    if not note_content or not isinstance(note_content, str):
        return "Error: note_content cannot be empty."

    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, sane_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(note_content)
        return f"Successfully saved note to '{output_path}'."
    except IOError as e:
        return f"Error: Failed to write note to file '{output_path}'. Reason: {e}"


# --- New Filename Check Tool ---
class CheckFilenameInput(BaseModel):
    """Input schema for the check_filename_exists tool."""
    filename: str = Field(description="The filename to check for existence in the './output' directory. Example: 'my_meeting_summary.md'")

@tool(args_schema=CheckFilenameInput)
def check_filename_exists(filename: str) -> str:
    """
    Checks if a file with the given name already exists in the './output' directory.
    Use this tool before saving a new note to avoid overwriting existing files.
    If the agent wants to create a new version, it should propose a new name (e.g., 'my_file_v2.md').
    """
    # Use the same sanitization as the save_note tool for a consistent check.
    sane_filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
    if sane_filename != filename or ".." in filename or "/" in filename or "\\" in filename:
        return f"Error: Invalid filename '{filename}'. Filename should not contain paths or special characters."
    
    if not sane_filename.endswith(".md"):
        sane_filename += ".md"

    output_path = os.path.join(OUTPUT_DIR, sane_filename)

    if os.path.exists(output_path):
        return f"Observation: Filename '{sane_filename}' already exists in the output directory. You should choose a different name to avoid overwriting it."
    else:
        return f"Observation: Filename '{sane_filename}' is available and can be used."


# --- Tool Registry ---
local_tools_list = [
    read_local_document,
    translate_english_to_chinese,
    save_note,
    check_filename_exists,
]

