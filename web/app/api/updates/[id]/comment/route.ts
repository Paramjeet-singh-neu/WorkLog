import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/session";

const apiBaseUrl = process.env.WORKLOG_API_URL ?? "http://127.0.0.1:8000";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await context.params;
  const payload = (await request.json()) as { body?: string };

  const response = await fetch(
    `${apiBaseUrl}/updates/${id}/comments?author_discord_id=${encodeURIComponent(session.id)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body: payload.body ?? "" }),
      cache: "no-store",
    },
  );

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}
