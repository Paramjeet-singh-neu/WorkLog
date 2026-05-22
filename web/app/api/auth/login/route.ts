import { randomBytes } from "crypto";
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { oauthRedirectUri } from "@/lib/auth";
import { discordLoginUrl } from "@/lib/discord";

export async function GET(request: NextRequest) {
  const state = randomBytes(24).toString("base64url");
  const redirectUri = oauthRedirectUri(request);
  const cookieStore = await cookies();

  cookieStore.set("worklog_oauth_state", state, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 10,
  });
  cookieStore.set("worklog_oauth_redirect", redirectUri, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 10,
  });

  return NextResponse.redirect(discordLoginUrl(state, redirectUri));
}
