"""
Exposes the notes_generator tool for easy import.
"""
from .tool import refine_and_generate_note

notes_tools = [refine_and_generate_note]

__all__ = ["notes_tools"]
