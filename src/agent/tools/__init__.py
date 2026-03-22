"""
This module centralizes all tools available to the agent, combining remote
MCP tools with locally defined tools, and adapting them for compatibility.
"""
from .mcp_tools import mcp_tools
from .local_tools import local_tools_list
from .tool_adapters import adapt_tool_for_classic_agent
from agent.utils.logging import logger

# 1. First, gather all tools from different sources into a temporary dict.
unadapted_tools = {}
unadapted_tools.update(mcp_tools)
for tool in local_tools_list:
    if tool.name in unadapted_tools:
        logger.warning(
            f"Local tool '{tool.name}' conflicts with an existing tool and will be overwritten."
        )
    unadapted_tools[tool.name] = tool

# 2. Now, create the final 'all_tools' dict by applying the compatibility adapter.
#    This makes modern tools work with the classic agent executor.
all_tools = {}
for name, tool in unadapted_tools.items():
    all_tools[name] = adapt_tool_for_classic_agent(tool)
    
logger.info(f"Loaded and adapted {len(all_tools)} tools. Names: {list(all_tools.keys())}")

__all__ = ["all_tools"]
