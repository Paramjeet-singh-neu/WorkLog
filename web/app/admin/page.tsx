import { getAdminSummary } from "@/lib/api";

const cards: Array<{ key: keyof Awaited<ReturnType<typeof getAdminSummary>>; label: string }> = [
  { key: "users", label: "Users" },
  { key: "projects", label: "Projects" },
  { key: "updates", label: "Updates" },
  { key: "comments", label: "Comments" },
  { key: "kudos", label: "Kudos" },
  { key: "blocked_updates", label: "Blockers" },
  { key: "review_requests", label: "Review requests" },
];

export default async function AdminPage() {
  try {
    const summary = await getAdminSummary();

    return (
      <div className="stack">
        <section className="card">
          <p className="pill">Admin</p>
          <h1>Cohort health</h1>
          <p className="muted">Lightweight operating dashboard for Worklog activity.</p>
        </section>

        <section className="metric-grid">
          {cards.map((card) => (
            <article className="card metric" key={card.key}>
              <p className="muted">{card.label}</p>
              <strong>{summary[card.key]}</strong>
            </article>
          ))}
        </section>
      </div>
    );
  } catch {
    return (
      <section className="card stack">
        <p className="pill">Admin</p>
        <h1>Admin summary unavailable</h1>
        <p className="muted">
          Add DIGEST_TRIGGER_TOKEN to the web environment so the server can call the protected
          admin API.
        </p>
      </section>
    );
  }
}
