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

function getPreview(messages: Array<{ type: string; content: unknown }>) {
  const firstHuman = messages.find((message) => message.type === "human");
  if (!firstHuman) return "Untitled thread";
  if (typeof firstHuman.content === "string") return firstHuman.content;
  if (Array.isArray(firstHuman.content)) {
    const textPart = firstHuman.content.find(
      (part: any) => typeof part === "object" && part?.type === "text",
    ) as { text?: string } | undefined;
    return textPart?.text ?? "Untitled thread";
  }
  return "Untitled thread";
}

export async function GET() {
  try {
    const sessionsDir = getSessionsDir();
    const files = await fs.readdir(sessionsDir);
    const items = await Promise.all(
      files
        .filter((file) => file.endsWith(".json"))
        .map(async (file) => {
          const raw = await fs.readFile(path.join(sessionsDir, file), "utf-8");
          const session = JSON.parse(raw);
          const messages = Array.isArray(session.messages)
            ? session.messages.map(normalizeMessage)
            : [];
          return {
            thread_id: session.thread_id ?? file.replace(/\.json$/, ""),
            updated_at: session.updated_at ?? null,
            active_note_id: session.active_note_id ?? null,
            active_note_title: session.active_note_title ?? null,
            mode: normalizeMode(session.mode),
            values: {
              messages,
            },
            preview: getPreview(messages),
          };
        }),
    );

    items.sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""));
    return NextResponse.json({ threads: items });
  } catch (error: any) {
    if (error?.code === "ENOENT") {
      return NextResponse.json({ threads: [] });
    }
    return NextResponse.json(
      { error: "Failed to load session history." },
      { status: 500 },
    );
  }
}
