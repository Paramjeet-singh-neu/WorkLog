import type { NextRequest } from "next/server";

export function oauthRedirectUri(request: NextRequest | Request): string {
  const configured = process.env.DISCORD_REDIRECT_URI?.trim();
  if (configured) {
    return configured;
  }

  return new URL("/api/auth/callback/discord", request.url).toString();
}
