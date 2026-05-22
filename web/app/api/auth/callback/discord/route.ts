import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { oauthRedirectUri } from "@/lib/auth";
import { exchangeCodeForSession } from "@/lib/discord";
import { setSession } from "@/lib/session";

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const cookieStore = await cookies();
  const expectedState = cookieStore.get("worklog_oauth_state")?.value;
  const redirectUri =
    cookieStore.get("worklog_oauth_redirect")?.value ?? oauthRedirectUri(request);

  if (!code || !state || !expectedState || state !== expectedState) {
    return NextResponse.redirect(new URL("/?auth=failed", request.url));
  }

  try {
    const session = await exchangeCodeForSession(code, redirectUri);
    await setSession(session);
    cookieStore.delete("worklog_oauth_state");
    cookieStore.delete("worklog_oauth_redirect");
    return NextResponse.redirect(new URL("/", request.url));
  } catch {
    return NextResponse.redirect(new URL("/?auth=failed", request.url));
  }
}
