import asyncio
import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict

# 将 src 目录添加到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import uvicorn

from agent.graph import graph as agent_graph
from agent.session import run_interactive_session, run_from_file
from agent.utils.logging import logger

# --- File Paths ---
# Build paths relative to this file's location to ensure they are robust
# Project root is 3 levels up from src/agent/main.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"


# --- FastAPI App Setup ---
app = FastAPI()

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StreamRequest(BaseModel):
    """Request model for the streaming endpoint."""
    input: str
    thread_id: str | None = None

# --- API Endpoints ---

@app.get("/")
async def serve_frontend():
    """Serves the frontend's index.html file."""
    return FileResponse(FRONTEND_DIR / "index.html")

@app.post("/agent/stream")
async def stream_agent(req: StreamRequest):
    """
    Main streaming endpoint for the agent.
    Streams events from the graph execution using Server-Sent Events (SSE).
    """
    logger.info(f"Received stream request with input: '{req.input}'")

    async def event_generator():
        # The config for the stream needs a thread_id to be stateful
        config = {"configurable": {"thread_id": "note-agent-thread-1"}}

        # Use astream_events to get detailed events
        async for event in agent_graph.astream_events(
            {"user_input": req.input},
            config,
            version="v1"
        ):
            event_name = event["event"]

            if event_name not in ["on_chain_stream", "on_chain_end"]:
                continue

            tags = event.get("tags", [])
            node_name = next((tag.replace("langgraph:node:", "") for tag in tags if tag.startswith("langgraph:node:")), None)

            if not node_name:
                continue

            # For streaming chunks of text
            if event_name == "on_chain_stream":
                chunk = event["data"].get("chunk")
                data_to_send = None
                if isinstance(chunk, Dict) and "content" in chunk:
                    data_to_send = chunk["content"]
                elif isinstance(chunk, str):
                    data_to_send = chunk

                if data_to_send:
                    yield f"data: {json.dumps({'event': 'data', 'node': node_name, 'content': data_to_send})}\n\n"

            # When a node finishes its execution
            elif event_name == "on_chain_end":
                output = event["data"].get("output")
                if output:
                    yield f"data: {json.dumps({'event': 'end', 'node': node_name, 'data': output})}\n\n"

    return EventSourceResponse(event_generator())


# --- CLI and Main Execution ---
# (Rest of the file remains the same)


# --- CLI and Main Execution ---

def generate_graph_image():
    """
    生成并保存 Agent 工作流的 PNG 图像。
    """
    logger.info("Generating agent workflow graph...")
    try:
        # Correctly call the get_graph() method on the *compiled* agent_graph object
        png_bytes = agent_graph.get_graph(xray=True).draw_mermaid_png()
        output_path = Path(__file__).parent.parent.parent / "agent_graph.png"
        with open(output_path, "wb") as f:
            f.write(png_bytes)
        logger.info(f"Graph image saved to: {output_path}")
    except Exception as e:
        logger.error(f"An error occurred while generating the graph: {e}", exc_info=True)
        logger.warning(
            "Please ensure 'pyppeteer' is installed (`pip install pyppeteer`) and internet connection is working."
        )

def main():
    """
    Agent 的主入口点。
    根据命令行参数选择运行模式：交互式、从文件读取或作为Web服务器。
    """
    parser = argparse.ArgumentParser(description="Note Agent CLI")
    parser.add_argument(
        "--file",
        action="store_true",
        help="Run the agent once from 'data/inputs.json'."
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run the agent as a FastAPI web server."
    )
    args = parser.parse_args()

    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    generate_graph_image()

    if args.serve:
        logger.info("Serve mode activated. Starting FastAPI server.")
        uvicorn.run(app, host="127.0.0.1", port=8000)
    elif args.file:
        logger.info("File mode activated. Running once from inputs.json.")
        asyncio.run(run_from_file())
    else:
        logger.info("Interactive mode activated. Starting session.")
        asyncio.run(run_interactive_session())

if __name__ == "__main__":
    main()
