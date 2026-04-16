from __future__ import annotations

import base64
import mimetypes
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from agent.dispatcher.schemas import ExtractedData
from agent.utils.logging import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = PROJECT_ROOT / "server_tmp" / "uploads"
SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
MIME_EXTENSION_OVERRIDES = {
    "application/pdf": ".pdf",
    "text/markdown": ".md",
    "text/plain": ".txt",
}


def _extract_thread_id(config: RunnableConfig | None) -> str | None:
    if not config:
        return None
    configurable = config.get("configurable", {})
    if not isinstance(configurable, dict):
        return None
    thread_id = configurable.get("thread_id")
    return str(thread_id) if thread_id else None


def _latest_human_message(messages: list[Any]) -> Any | None:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message
        if isinstance(message, dict) and (message.get("type") or message.get("role")) in {"human", "user"}:
            return message
    return None


def _content_parts(message: Any) -> list[Any]:
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    if isinstance(content, list):
        return content
    return []


def _safe_filename(filename: str, mime_type: str) -> str:
    original = (filename or "").strip()
    stem, ext = os.path.splitext(original)
    stem = SAFE_FILENAME_RE.sub("_", stem or "upload").strip("._") or "upload"
    ext = ext or MIME_EXTENSION_OVERRIDES.get(mime_type) or mimetypes.guess_extension(mime_type or "") or ""
    return f"{uuid4().hex[:8]}_{stem}{ext}"


def _save_file_block(part: dict[str, Any], thread_id: str | None) -> str | None:
    data = part.get("data")
    if not isinstance(data, str) or not data.strip():
        return None

    mime_type = str(part.get("mimeType") or "")
    metadata = part.get("metadata") if isinstance(part.get("metadata"), dict) else {}
    filename = str(metadata.get("filename") or metadata.get("name") or "upload")

    subdir = UPLOAD_DIR / (thread_id or "adhoc")
    subdir.mkdir(parents=True, exist_ok=True)
    target = subdir / _safe_filename(filename, mime_type)

    try:
        raw = base64.b64decode(data)
        target.write_bytes(raw)
        return str(target)
    except Exception as exc:
        logger.warning("Failed to persist uploaded file block '%s': %s", filename, exc)
        return None


def normalize_input_node(state: dict[str, Any], config: RunnableConfig | None = None) -> dict[str, Any]:
    """
    Normalize the latest human message into structured extracted_data entries.
    Current minimal support:
    - text stays in the original message history
    - file blocks are persisted and exposed as ExtractedData(type='file_path')
    - image blocks are ignored for now
    """
    messages = state.get("messages", []) or []
    latest_message = _latest_human_message(messages)
    if latest_message is None:
        return {"extracted_data": state.get("extracted_data") or []}

    thread_id = _extract_thread_id(config)
    extracted: list[ExtractedData] = list(state.get("extracted_data") or [])

    for part in _content_parts(latest_message):
        if not isinstance(part, dict):
            continue
        if part.get("type") != "file":
            continue
        saved_path = _save_file_block(part, thread_id)
        if saved_path:
            extracted.append(ExtractedData(type="file_path", content=saved_path))

    return {"extracted_data": extracted}


__all__ = ["normalize_input_node"]
