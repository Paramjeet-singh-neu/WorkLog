import { NextResponse } from "next/server";
import { getSession } from "@/lib/session";

const apiBaseUrl = process.env.WORKLOG_API_URL ?? "http://127.0.0.1:8000";

export async function POST(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await context.params;
  const response = await fetch(
    `${apiBaseUrl}/updates/${id}/kudos?user_discord_id=${encodeURIComponent(session.id)}`,
    { method: "POST", cache: "no-store" },
  );

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}
