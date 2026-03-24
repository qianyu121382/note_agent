"""
This module defines local tools for the agent that interact with the local filesystem or perform local computations.
"""
import os
from langchain_core.tools import tool
from pypdf import PdfReader

# Import shared LLM and necessary components for the new tool
from agent.llm import llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


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

# 1. Define the chain for the translation tool
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
        translated_text = _translation_chain.invoke({"english_text": text})
        return translated_text
    except Exception as e:
        # Return a simple error message to the agent instead of a full traceback
        return f"Error: An exception occurred during translation. Reason: {e}"


# --- Tool Registry ---
# A list of all tools defined in this module, so they can be discovered by the agent.
local_tools_list = [
    read_local_document,
    translate_english_to_chinese,
]
