from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from langchain_core.messages import BaseMessage, messages_to_dict
from psycopg import connect

TABLE_NAME = "session_history_projection"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_postgres_uri() -> Optional[str]:
    value = os.getenv("POSTGRES_URI")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _ensure_table() -> None:
    postgres_uri = _get_postgres_uri()
    if not postgres_uri:
        return

    with connect(postgres_uri, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    thread_id TEXT PRIMARY KEY,
                    updated_at TIMESTAMPTZ NOT NULL,
                    preview TEXT NOT NULL DEFAULT '',
                    intent TEXT,
                    mode TEXT NOT NULL DEFAULT 'idle',
                    operation TEXT NOT NULL DEFAULT 'none',
                    active_note_id TEXT,
                    active_note_title TEXT,
                    messages JSONB NOT NULL DEFAULT '[]'::jsonb
                )
                """
            )
            cur.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_updated_at
                ON {TABLE_NAME} (updated_at DESC)
                """
            )
            cur.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_active_note_id
                ON {TABLE_NAME} (active_note_id)
                """
            )


def _normalize_message_content(content: Any) -> Any:
    if isinstance(content, (str, list)):
        return content
    return content if content is not None else ""


def _build_preview(messages: list[BaseMessage]) -> str:
    for message in messages:
        if getattr(message, "type", None) != "human":
            continue
        content = getattr(message, "content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            parts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            text = "".join(parts).strip()
            if text:
                return text
    return "Untitled thread"


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
    """Persist a frontend-facing session history projection in PostgreSQL.

    LangGraph API owns thread-scoped short-term memory. This table is a
    projection optimized for frontend history list/detail queries.
    """
    postgres_uri = _get_postgres_uri()
    if not postgres_uri:
        return

    _ensure_table()
    updated_at = _now_iso()
    preview = _build_preview(messages)
    message_payload = messages_to_dict(messages)

    for item in message_payload:
        data = item.get("data", {})
        if isinstance(data, dict):
            data["content"] = _normalize_message_content(data.get("content"))

    with connect(postgres_uri, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    thread_id,
                    updated_at,
                    preview,
                    intent,
                    mode,
                    operation,
                    active_note_id,
                    active_note_title,
                    messages
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (thread_id) DO UPDATE SET
                    updated_at = EXCLUDED.updated_at,
                    preview = EXCLUDED.preview,
                    intent = EXCLUDED.intent,
                    mode = EXCLUDED.mode,
                    operation = EXCLUDED.operation,
                    active_note_id = EXCLUDED.active_note_id,
                    active_note_title = EXCLUDED.active_note_title,
                    messages = EXCLUDED.messages
                """,
                (
                    thread_id,
                    updated_at,
                    preview,
                    intent,
                    mode or "idle",
                    operation or "none",
                    active_note_id,
                    active_note_title,
                    json.dumps(message_payload, ensure_ascii=False),
                ),
            )


__all__ = ["TABLE_NAME", "export_session_snapshot"]
