"""
Dispatcher Subgraph.

This module is responsible for analyzing the user input and routing
the workflow accordingly.
"""
from .node import dispatch

__all__ = ["dispatch"]
