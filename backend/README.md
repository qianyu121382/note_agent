# Note Agent Backend

This directory contains the active LangGraph backend project.

## Run Locally

```bash
cd backend
pip install -e .
langgraph dev
```

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
