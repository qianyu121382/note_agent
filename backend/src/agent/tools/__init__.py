"""
Toolbox for the Note Agent.

Keep this package lazy. Service/storage modules import submodules under
`agent.tools`, so eagerly importing every tool here would create circular
imports through `local_tools`.
"""

from __future__ import annotations

from typing import Any


def _load_all_tools() -> list[Any]:
    notes_tools = []
    local_tools_list = []
    mcp_tools = {}

    try:
        from .notes_generator import notes_tools as loaded_notes_tools

        notes_tools = loaded_notes_tools
    except ModuleNotFoundError:
        notes_tools = []

    try:
        from .local_tools import local_tools_list as loaded_local_tools_list

        local_tools_list = loaded_local_tools_list
    except ModuleNotFoundError:
        local_tools_list = []

    try:
        from .mcp_tools import mcp_tools as loaded_mcp_tools

        mcp_tools = loaded_mcp_tools
    except ModuleNotFoundError:
        mcp_tools = {}

    return notes_tools + local_tools_list + list(mcp_tools.values())


def __getattr__(name: str):
    if name == "all_tools":
        return _load_all_tools()
    if name == "all_tools_map":
        tools = _load_all_tools()
        return {tool.name: tool for tool in tools}
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "all_tools",
    "all_tools_map",
]
