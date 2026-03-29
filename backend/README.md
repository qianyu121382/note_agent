# Note Agent Backend

This directory contains the active LangGraph backend project.

## Persistence

This backend follows the standard LangGraph API pattern:

- do not attach a custom checkpointer in `src/agent/graph.py`
- let `langgraph dev` manage thread persistence automatically
- configure PostgreSQL with `POSTGRES_URI` in `.env`

Session history is stored in PostgreSQL as a frontend-facing projection table. It is not the primary short-term memory store; LangGraph persistence remains the source of truth for thread state.

## Run Locally

```bash
cd backend
pip install -e .
langgraph dev
```

Before starting, set `POSTGRES_URI` in `.env` if you want persistent thread
memory across restarts.

Or run the CLI loop:

```bash
cd backend
python -m src.agent.main
```

## Frontend Connection

Use these values in Agent Chat UI:

- `Graph ID`: `note_agent`
- `Deployment URL`: `http://127.0.0.1:2024`

## Layout

- `src/agent`: main LangGraph application
- `data`: inputs and generated notes
- `server_tmp`: server-side downloaded temporary files
- `tests`: current test files

