import Link from "next/link";
import { redirect } from "next/navigation";
import { getUserByDiscordId, getUserProfile } from "@/lib/api";
import { getSession } from "@/lib/session";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default async function ProfilePage() {
  const session = await getSession();
  if (!session) {
    redirect("/api/auth/login");
  }

  const user = await getUserByDiscordId(session.id);
  if (!user) {
    return (
      <section className="card stack">
        <h1>No Worklog profile yet</h1>
        <p className="muted">
          Use `/skills` or `/post progress` in Discord first, then refresh this page.
        </p>
      </section>
    );
  }

  const profile = await getUserProfile(user.id);

  return (
    <div className="stack">
      <section className="card">
        <p className="pill">Profile</p>
        <h1>{profile.user.name}</h1>
        <p className="muted">{profile.user.skills_text ?? "No skills saved yet."}</p>
      </section>

      <section className="card stack">
        <h2>Recent Updates</h2>
        {profile.updates.length === 0 ? (
          <p className="muted">No updates yet.</p>
        ) : (
          profile.updates.map((update) => (
            <article key={update.id}>
              <strong>{update.kind}</strong>
              <p>{update.body}</p>
              <p className="muted">{formatDate(update.created_at)}</p>
            </article>
          ))
        )}
      </section>

      <section className="card stack">
        <h2>Projects</h2>
        {profile.projects.length === 0 ? (
          <p className="muted">No projects yet. Phase 2 only views project data once it exists.</p>
        ) : (
          profile.projects.map((project) => (
            <article key={project.id}>
              <Link href={`/projects/${project.id}`}>
                <strong>{project.title}</strong>
              </Link>
              <p className="muted">{project.status}</p>
            </article>
          ))
        )}
      </section>
    </div>
  );
}
