"""
Toolbox for the Note Agent.

This module aggregates all callable tools from the 'tools' directory
for easy import and registration with an agent.
"""
from .notes_generator import notes_tools
from .local_tools import local_tools_list
from .mcp_tools import mcp_tools

# A single list containing all tools for the agent
all_tools = notes_tools + local_tools_list + list(mcp_tools.values())

# Create a dictionary for easy lookup
all_tools_map = {tool.name: tool for tool in all_tools}

__all__ = [
    "all_tools",
    "all_tools_map",
]
