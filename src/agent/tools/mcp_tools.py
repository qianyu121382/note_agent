"""
This module initializes the MCP client and fetches tools from the remote server.
"""
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool

from agent.utils.logging import logger

# User-provided MCP configuration.
# The key 'fetch' is a local alias for this server connection.
MCP_CONFIG = {
    "fetch": {
        # The client expects the key to be 'transport', not 'type'.
        "transport": "sse",
        "url": "https://mcp.api-inference.modelscope.net/6be788ed9cbf40/sse"
    }
}

async def _initialize_tools_from_mcp() -> dict[str, BaseTool]:
    """
    Initializes the MCP client and fetches all available tools,
    returning them in a dictionary keyed by their names.
    """
    tool_dict = {}
    try:
        logger.info("Initializing MCP client and fetching remote tools...")
        client = MultiServerMCPClient(MCP_CONFIG)
        tools = await client.get_tools()
        
        if not tools:
            raise RuntimeError("MCP server did not return any tools.")
            
        for tool in tools:
            logger.info(f"Successfully fetched tool: {tool.name}")
            tool_dict[tool.name] = tool
            
        return tool_dict
    except Exception as e:
        logger.error(f"Failed to initialize MCP tools: {e}")
        # In case of failure, return an empty dict.
        return {}

# Run the async initialization function at module load time.
# The result is a dictionary of tools that can be imported elsewhere.
# This ensures we only initialize the client and fetch tools once.
logger.info("Fetching MCP tools at module load...")
# Note: Using asyncio.run() here is a simple way to handle async initialization
# in a synchronous context. It creates a new event loop.
mcp_tools = asyncio.run(_initialize_tools_from_mcp())
