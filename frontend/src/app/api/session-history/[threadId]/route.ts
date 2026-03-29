import { NextResponse } from "next/server";

import { getSessionHistory } from "@/lib/session-history-store";

export const runtime = "nodejs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ threadId: string }> },
) {
  try {
    const { threadId } = await context.params;
    const session = await getSessionHistory(threadId);

    if (!session) {
      return NextResponse.json({
        thread_id: threadId,
        updated_at: null,
        active_note_id: null,
        active_note_title: null,
        mode: "idle",
        messages: [],
      });
    }

    return NextResponse.json({
      thread_id: session.thread_id,
      updated_at: session.updated_at,
      active_note_id: session.active_note_id,
      active_note_title: session.active_note_title,
      mode: session.mode,
      messages: session.values.messages,
    });
  } catch {
    return NextResponse.json(
      { error: "Failed to load session detail." },
      { status: 500 },
    );
  }
}
