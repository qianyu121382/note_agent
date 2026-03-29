import { NextResponse } from "next/server";

import { listSessionHistory } from "@/lib/session-history-store";

export const runtime = "nodejs";

export async function GET() {
  try {
    const threads = await listSessionHistory(100);
    return NextResponse.json({ threads });
  } catch {
    return NextResponse.json(
      { error: "Failed to load session history." },
      { status: 500 },
    );
  }
}
