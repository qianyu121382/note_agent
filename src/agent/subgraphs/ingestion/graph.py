"""
Ingestion Sub-Graph.

This graph is responsible for taking the data extracted by the dispatcher,
parsing it, and integrating the content.
"""
from langgraph.graph import StateGraph, END
from agent.state import AgentState

# Import nodes from the current subgraph
from .nodes.splitter import split_extracted_data
from .nodes.text_parser import parse_texts
from .nodes.url_parser import parse_urls
from .nodes.integrator import integrate_content

# --- Ingestion Sub-Graph Definition ---
workflow = StateGraph(AgentState)
workflow.add_node("split_data", split_extracted_data)
workflow.add_node("parse_urls", parse_urls)
workflow.add_node("parse_texts", parse_texts)
workflow.add_node("integrate_content", integrate_content)

workflow.set_entry_point("split_data")
workflow.add_edge("split_data", "parse_urls")
workflow.add_edge("split_data", "parse_texts")
workflow.add_edge("parse_urls", "integrate_content")
workflow.add_edge("parse_texts", "integrate_content")
workflow.add_edge("integrate_content", END) # End of sub-graph

ingestion_graph = workflow.compile()
ingestion_graph.name = "内容提取子图"
