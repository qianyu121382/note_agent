import { promises as fs } from "fs";
import path from "path";

import { NextResponse } from "next/server";

export const runtime = "nodejs";

function getSessionsDir() {
  return path.resolve(process.cwd(), "..", "backend", "data", "sessions");
}

function normalizeContent(content: unknown) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content;
  return content ?? "";
}

function normalizeMode(mode: unknown) {
  return mode === "create" || mode === "edit" || mode === "qa"
    ? mode
    : "idle";
}

function normalizeMessage(message: any, index: number) {
  const type = message?.type ?? message?.data?.type ?? "ai";
  const data = message?.data ?? {};
  const normalizedType = type === "human" || type === "ai" || type === "tool" ? type : "ai";
  return {
    id: data.id ?? `${normalizedType}-${index}`,
    type: normalizedType,
    content: normalizeContent(data.content),
  };
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ threadId: string }> },
) {
  try {
    const { threadId } = await context.params;
    const filePath = path.join(getSessionsDir(), `${threadId}.json`);

    try {
      const raw = await fs.readFile(filePath, "utf-8");
      const session = JSON.parse(raw);
      const messages = Array.isArray(session.messages)
        ? session.messages.map(normalizeMessage)
        : [];

      return NextResponse.json({
        thread_id: session.thread_id ?? threadId,
        updated_at: session.updated_at ?? null,
        active_note_id: session.active_note_id ?? null,
        active_note_title: session.active_note_title ?? null,
        mode: normalizeMode(session.mode),
        messages,
      });
    } catch (error: any) {
      if (error?.code === "ENOENT") {
        return NextResponse.json({
          thread_id: threadId,
          updated_at: null,
          active_note_id: null,
          active_note_title: null,
          mode: "idle",
          messages: [],
        });
      }
      throw error;
    }
  } catch {
    return NextResponse.json(
      { error: "Failed to load session detail." },
      { status: 500 },
    );
  }
}
