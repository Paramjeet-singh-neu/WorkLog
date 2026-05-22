import type { DiscordSession } from "./types";

const discordApiBase = "https://discord.com/api/v10";

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

export function discordLoginUrl(state: string, redirectUri: string): string {
  const params = new URLSearchParams({
    client_id: requiredEnv("DISCORD_CLIENT_ID"),
    redirect_uri: redirectUri,
    response_type: "code",
    scope: "identify",
    state,
  });

  return `${discordApiBase}/oauth2/authorize?${params.toString()}`;
}

export async function exchangeCodeForSession(
  code: string,
  redirectUri: string,
): Promise<DiscordSession> {
  const tokenResponse = await fetch(`${discordApiBase}/oauth2/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      client_id: requiredEnv("DISCORD_CLIENT_ID"),
      client_secret: requiredEnv("DISCORD_CLIENT_SECRET"),
      grant_type: "authorization_code",
      code,
      redirect_uri: redirectUri,
    }),
  });

  if (!tokenResponse.ok) {
    throw new Error(`Discord token exchange failed: ${tokenResponse.status}`);
  }

  const token = (await tokenResponse.json()) as { access_token: string };
  const userResponse = await fetch(`${discordApiBase}/users/@me`, {
    headers: {
      Authorization: `Bearer ${token.access_token}`,
    },
  });

  if (!userResponse.ok) {
    throw new Error(`Discord user fetch failed: ${userResponse.status}`);
  }

  const user = (await userResponse.json()) as {
    id: string;
    username: string;
    avatar: string | null;
  };

  return {
    id: user.id,
    username: user.username,
    avatar: user.avatar,
  };
}
