import type {
  AdminSummary,
  Project,
  ProjectSocial,
  ShowcaseProject,
  Update,
  UpdateSocial,
  UserProfile,
  WorklogUser,
} from "./types";

const apiBaseUrl = process.env.WORKLOG_API_URL ?? "http://127.0.0.1:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Worklog API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getFeed(): Promise<Update[]> {
  return fetchJson<Update[]>("/updates?limit=50");
}

export async function getUpdate(updateId: number): Promise<Update> {
  return fetchJson<Update>(`/updates/${updateId}`);
}

export async function getRankedFeed(viewerDiscordId: string): Promise<Update[]> {
  return fetchJson<Update[]>(
    `/feed?viewer_discord_id=${encodeURIComponent(viewerDiscordId)}&limit=50`,
  );
}

export async function markFeedSeen(viewerDiscordId: string, updateIds: number[]): Promise<void> {
  if (updateIds.length === 0) {
    return;
  }

  const response = await fetch(
    `${apiBaseUrl}/feed/seen?viewer_discord_id=${encodeURIComponent(viewerDiscordId)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ update_ids: updateIds }),
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(`Worklog API request failed: ${response.status}`);
  }
}

export async function getUserByDiscordId(discordId: string): Promise<WorklogUser | null> {
  const response = await fetch(`${apiBaseUrl}/users/discord/${discordId}`, {
    cache: "no-store",
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Worklog API request failed: ${response.status}`);
  }

  return response.json() as Promise<WorklogUser>;
}

export async function getUserProfile(userId: number): Promise<UserProfile> {
  return fetchJson<UserProfile>(`/users/${userId}`);
}

export async function getProject(projectId: string): Promise<Project> {
  return fetchJson<Project>(`/projects/${projectId}`);
}

export async function getProjectUpdates(projectId: string): Promise<Update[]> {
  return fetchJson<Update[]>(`/projects/${projectId}/updates`);
}

export async function getProjectSocial(
  projectId: string,
  viewerDiscordId?: string,
): Promise<ProjectSocial> {
  const params = viewerDiscordId
    ? `?viewer_discord_id=${encodeURIComponent(viewerDiscordId)}`
    : "";
  return fetchJson<ProjectSocial>(`/projects/${projectId}/social${params}`);
}

export async function getShowcase(): Promise<ShowcaseProject[]> {
  return fetchJson<ShowcaseProject[]>("/showcase?limit=20");
}

export async function getAdminSummary(): Promise<AdminSummary> {
  const headers: HeadersInit = {};
  if (process.env.DIGEST_TRIGGER_TOKEN) {
    headers.Authorization = `Bearer ${process.env.DIGEST_TRIGGER_TOKEN}`;
  }

  const response = await fetch(`${apiBaseUrl}/admin/summary`, {
    cache: "no-store",
    headers,
  });

  if (!response.ok) {
    throw new Error(`Worklog API request failed: ${response.status}`);
  }

  return response.json() as Promise<AdminSummary>;
}

export async function getBatchSocial(
  updateIds: number[],
  viewerDiscordId?: string,
): Promise<Record<number, UpdateSocial>> {
  if (updateIds.length === 0) {
    return {};
  }

  const params = new URLSearchParams({ update_ids: updateIds.join(",") });
  if (viewerDiscordId) {
    params.set("viewer_discord_id", viewerDiscordId);
  }

  const raw = await fetchJson<Record<string, UpdateSocial>>(`/social?${params.toString()}`);
  return Object.fromEntries(
    Object.entries(raw).map(([key, value]) => [Number(key), value]),
  ) as Record<number, UpdateSocial>;
}

export async function getUpdateSocial(
  updateId: number,
  viewerDiscordId?: string,
): Promise<UpdateSocial> {
  const params = viewerDiscordId
    ? `?viewer_discord_id=${encodeURIComponent(viewerDiscordId)}`
    : "";
  return fetchJson<UpdateSocial>(`/updates/${updateId}/social${params}`);
}
