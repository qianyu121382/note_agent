"""
LLM Singleton Module for the Agent.

This module initializes and exports a single, reusable instance of the ChatOpenAI model,
configured with the necessary API keys and settings. This allows other parts of
the application to import and use the same LLM instance without re-initializing it.
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from agent.utils.logging import logger

# --- LLM Definition ---

# Load environment variables from a .env file in the project root.
# This file should contain your OpenAI API key, e.g., OPENAI_API_KEY="sk-..."
logger.info("Loading environment variables from .env file...")
load_dotenv()

# Check for the API key and raise an error if it's not found.
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError(
        "OPENAI_API_KEY not found in environment variables. "
        "Please create a .env file in the project root and add your key."
    )
# Initialize a single, reusable LLM instance for the entire application.
# Using a cost-effective and performant model like 'gpt-4o-mini' is a good start.
# The 'seed' parameter helps in achieving more reproducible outputs for the same inputs.
logger.info("Initializing ChatOpenAI model instance (gpt-4o-mini)...")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, seed=42)
