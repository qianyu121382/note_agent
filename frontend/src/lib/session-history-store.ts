import fs from "fs";
import path from "path";

import { Pool } from "pg";

const TABLE_NAME = "session_history_projection";

type RawMessage = {
  type?: string;
  data?: {
    id?: string;
    content?: unknown;
  };
};

export type SessionHistoryRecord = {
  thread_id: string;
  updated_at: string | null;
  preview: string;
  mode: "idle" | "create" | "edit" | "qa";
  active_note_id: string | null;
  active_note_title: string | null;
  values: {
    messages: Array<{
      id: string;
      type: string;
      content: unknown;
    }>;
  };
};

let pool: Pool | null = null;

function readBackendEnvPostgresUri(): string | null {
  try {
    const envPath = path.resolve(process.cwd(), "..", "backend", ".env");
    const text = fs.readFileSync(envPath, "utf-8");
    for (const line of text.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const idx = trimmed.indexOf("=");
      if (idx === -1) continue;
      const key = trimmed.slice(0, idx).trim();
      const value = trimmed.slice(idx + 1).trim();
      if (key === "POSTGRES_URI" && value) {
        return value;
      }
    }
  } catch {
    return null;
  }
  return null;
}

function getPostgresUri(): string | null {
  return process.env.POSTGRES_URI || readBackendEnvPostgresUri();
}

function getPool(): Pool {
  if (pool) return pool;

  const connectionString = getPostgresUri();
  if (!connectionString) {
    throw new Error("POSTGRES_URI is not configured for session history APIs.");
  }

  pool = new Pool({ connectionString });
  return pool;
}

function normalizeMode(mode: unknown): SessionHistoryRecord["mode"] {
  return mode === "create" || mode === "edit" || mode === "qa"
    ? mode
    : "idle";
}

function normalizeContent(content: unknown) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content;
  return content ?? "";
}

function normalizeMessage(message: RawMessage, index: number) {
  const normalizedType =
    message?.type === "human" || message?.type === "ai" || message?.type === "tool"
      ? message.type
      : "ai";

  return {
    id: message?.data?.id ?? `${normalizedType}-${index}`,
    type: normalizedType,
    content: normalizeContent(message?.data?.content),
  };
}

function normalizeRecord(row: any): SessionHistoryRecord {
  const rawMessages = Array.isArray(row.messages) ? row.messages : [];
  return {
    thread_id: String(row.thread_id),
    updated_at: row.updated_at ? new Date(row.updated_at).toISOString() : null,
    preview: typeof row.preview === "string" && row.preview.trim() ? row.preview : "Untitled thread",
    mode: normalizeMode(row.mode),
    active_note_id: row.active_note_id ?? null,
    active_note_title: row.active_note_title ?? null,
    values: {
      messages: rawMessages.map((message: RawMessage, index: number) => normalizeMessage(message, index)),
    },
  };
}

export async function listSessionHistory(limit = 100): Promise<SessionHistoryRecord[]> {
  const result = await getPool().query(
    `
      SELECT thread_id, updated_at, preview, mode, active_note_id, active_note_title, messages
      FROM ${TABLE_NAME}
      ORDER BY updated_at DESC
      LIMIT $1
    `,
    [limit],
  );

  return result.rows.map(normalizeRecord);
}

export async function getSessionHistory(threadId: string): Promise<SessionHistoryRecord | null> {
  const result = await getPool().query(
    `
      SELECT thread_id, updated_at, preview, mode, active_note_id, active_note_title, messages
      FROM ${TABLE_NAME}
      WHERE thread_id = $1
      LIMIT 1
    `,
    [threadId],
  );

  if (result.rows.length === 0) {
    return null;
  }

  return normalizeRecord(result.rows[0]);
}
