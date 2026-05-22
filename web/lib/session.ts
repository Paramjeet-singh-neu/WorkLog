import { createHmac, timingSafeEqual } from "crypto";
import { cookies } from "next/headers";
import type { DiscordSession } from "./types";

const cookieName = "worklog_session";

function authSecret(): string {
  const secret = process.env.WEB_AUTH_SECRET;
  if (!secret) {
    throw new Error("WEB_AUTH_SECRET is required");
  }
  return secret;
}

function sign(payload: string): string {
  return createHmac("sha256", authSecret()).update(payload).digest("base64url");
}

export function encodeSession(session: DiscordSession): string {
  const payload = Buffer.from(JSON.stringify(session)).toString("base64url");
  return `${payload}.${sign(payload)}`;
}

export function decodeSession(value: string | undefined): DiscordSession | null {
  if (!value) {
    return null;
  }

  const [payload, signature] = value.split(".");
  if (!payload || !signature) {
    return null;
  }

  const expected = sign(payload);
  const expectedBuffer = Buffer.from(expected);
  const signatureBuffer = Buffer.from(signature);
  if (
    expectedBuffer.length !== signatureBuffer.length ||
    !timingSafeEqual(expectedBuffer, signatureBuffer)
  ) {
    return null;
  }

  try {
    return JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as DiscordSession;
  } catch {
    return null;
  }
}

export async function getSession(): Promise<DiscordSession | null> {
  const cookieStore = await cookies();
  return decodeSession(cookieStore.get(cookieName)?.value);
}

export async function setSession(session: DiscordSession): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set(cookieName, encodeSession(session), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
}

export async function clearSession(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(cookieName);
}
