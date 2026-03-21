"""
Dispatcher Subgraph Prompts.
"""
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

PROMPTS_DIR = Path(__file__).parent

def load_prompt(file_name: str) -> str:
    """Loads a prompt from a file in the prompts directory."""
    file_path = PROMPTS_DIR / file_name
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found: {file_path}")

def create_dispatcher_prompt() -> ChatPromptTemplate:
    """Creates the prompt template for the dispatcher node."""
    system_prompt = load_prompt("system.txt")
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "用户输入: {user_input}"),
        ]
    )

__all__ = ["create_dispatcher_prompt"]
