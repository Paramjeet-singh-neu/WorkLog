export type WorklogUser = {
  id: number;
  discord_id: number;
  name: string;
  skills_text: string | null;
  created_at: string;
};

export type Project = {
  id: number;
  owner_id: number;
  title: string;
  description: string | null;
  status: "active" | "shipped" | "paused" | "abandoned";
  created_at: string;
};

export type Update = {
  id: number;
  project_id: number | null;
  author_id: number;
  kind: "shipped" | "progress" | "blocked" | "seeking_review";
  body: string;
  discord_message_id: number | null;
  created_at: string;
  author: WorklogUser;
  project: Project | null;
};

export type UserProfile = {
  user: WorklogUser;
  updates: Omit<Update, "author" | "project">[];
  projects: Project[];
};

export type DiscordSession = {
  id: string;
  username: string;
  avatar: string | null;
};

export type Comment = {
  id: number;
  update_id: number;
  author_id: number;
  body: string;
  created_at: string;
  author: WorklogUser;
};

export type UpdateSocial = {
  update_id: number;
  comments: Comment[];
  kudo_count: number;
  viewer_has_kudo: boolean;
};

export type ProjectSocial = {
  project_id: number;
  follower_count: number;
  viewer_following: boolean;
};

export type ShowcaseProject = {
  project: Project;
  owner: WorklogUser;
  update_count: number;
  shipped_count: number;
  follower_count: number;
  latest_update_at: string | null;
};

export type AdminSummary = {
  users: number;
  projects: number;
  updates: number;
  comments: number;
  kudos: number;
  blocked_updates: number;
  review_requests: number;
};
