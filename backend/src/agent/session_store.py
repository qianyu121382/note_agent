from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import BaseMessage, messages_to_dict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
SESSIONS_DIR = DATA_DIR / "sessions"



def _ensure_dirs() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)



def _session_path(thread_id: str) -> Path:
    return SESSIONS_DIR / f"{thread_id}.json"



def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()



def export_session_snapshot(
    *,
    thread_id: str,
    messages: list[BaseMessage],
    active_note_id: Optional[str] = None,
    active_note_title: Optional[str] = None,
    intent: Optional[str] = None,
    mode: Optional[str] = None,
    operation: Optional[str] = None,
) -> None:
    """Export the current LangGraph thread state for frontend history display.

    Runtime short-term memory is owned by LangGraph API persistence. This file
    is only a serialized projection for the frontend session-history API.
    """
    _ensure_dirs()
    payload: dict[str, Any] = {
        "thread_id": thread_id,
        "messages": messages_to_dict(messages),
        "active_note_id": active_note_id,
        "active_note_title": active_note_title,
        "intent": intent,
        "mode": mode,
        "operation": operation,
        "updated_at": _now_iso(),
    }
    _session_path(thread_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = ["export_session_snapshot"]



