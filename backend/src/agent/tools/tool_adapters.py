"""
This module provides adapter functions to wrap tools, making them compatible
with different agent runtimes or conventions.
"""
from langchain_core.tools import BaseTool
from typing import Type

def adapt_tool_for_classic_agent(tool_to_wrap: BaseTool) -> BaseTool:
    """
    This is the definitive solution to the classic agent executor vs. modern
    pydantic schema tools incompatibility.

    It dynamically creates a NEW BaseTool SUBCLASS that presents a classic,
    string-based `_run` method to the executor. Internally, this method
    translates the string input into the dictionary format expected by the
    original, modern tool.
    """
    # If the tool has no schema, it's already compatible.
    if not tool_to_wrap.args_schema or not hasattr(tool_to_wrap.args_schema, 'schema'):
        return tool_to_wrap

    schema_properties = tool_to_wrap.args_schema.schema().get('properties', {})
    
    # This adapter is designed only for tools that have exactly one argument.
    if len(schema_properties) != 1:
        return tool_to_wrap
        
    arg_name = list(schema_properties.keys())[0]

    # Dynamically create a new class that inherits from BaseTool
    class ClassicWrapper(BaseTool):
        name: str = tool_to_wrap.name
        description: str = tool_to_wrap.description

        def _run(self, tool_input: str) -> str:
            """
            This method is what the classic AgentExecutor calls. It receives a raw string.
            """
            try:
                # We wrap the string in the dict the original tool expects.
                input_dict = {arg_name: tool_input}
                # And call the original tool's logic.
                return tool_to_wrap.invoke(input_dict)
            except Exception as e:
                return f"Error while invoking wrapped tool '{self.name}': {e}"

        async def _arun(self, tool_input: str) -> str:
            """Asynchronous version of the _run method."""
            try:
                input_dict = {arg_name: tool_input}
                return await tool_to_wrap.ainvoke(input_dict)
            except Exception as e:
                return f"Error while invoking wrapped tool '{self.name}': {e}"

    return ClassicWrapper()
