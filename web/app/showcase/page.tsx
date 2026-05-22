import Link from "next/link";
import { getShowcase } from "@/lib/api";

function formatDate(value: string | null) {
  if (!value) {
    return "No updates yet";
  }
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

export default async function ShowcasePage() {
  const projects = await getShowcase();

  return (
    <div className="stack">
      <section className="card">
        <p className="pill">Showcase</p>
        <h1>Cohort projects</h1>
        <p className="muted">
          A public view of active projects, recent momentum, shipped work, and followers.
        </p>
      </section>

      {projects.length === 0 ? (
        <section className="card">
          <p className="muted">No projects yet.</p>
        </section>
      ) : (
        <section className="showcase-grid">
          {projects.map((item) => (
            <article className="card stack" key={item.project.id}>
              <div>
                <p className="pill">{item.project.status}</p>
                <h2>
                  <Link href={`/projects/${item.project.id}`}>{item.project.title}</Link>
                </h2>
                <p className="muted">by {item.owner.name}</p>
              </div>
              <p>{item.project.description ?? "No description yet."}</p>
              <p className="muted">
                {item.update_count} updates · {item.shipped_count} shipped ·{" "}
                {item.follower_count} followers
              </p>
              <p className="muted">Latest: {formatDate(item.latest_update_at)}</p>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
