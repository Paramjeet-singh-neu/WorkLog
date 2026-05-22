import { notFound } from "next/navigation";
import { ProjectFollowButton } from "@/components/ProjectFollowButton";
import { getProject, getProjectSocial, getProjectUpdates } from "@/lib/api";
import { getSession } from "@/lib/session";

type PageProps = {
  params: Promise<{
    id: string;
  }>;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default async function ProjectPage({ params }: PageProps) {
  const { id } = await params;
  const session = await getSession();

  try {
    const [project, updates, social] = await Promise.all([
      getProject(id),
      getProjectUpdates(id),
      getProjectSocial(id, session?.id),
    ]);

    return (
      <div className="stack">
        <section className="card">
          <p className="pill">{project.status}</p>
          <h1>{project.title}</h1>
          <p className="muted">{project.description ?? "No project description yet."}</p>
          <ProjectFollowButton
            projectId={project.id}
            initial={social}
            canInteract={Boolean(session)}
          />
        </section>

        <section className="card stack">
          <h2>Project Updates</h2>
          {updates.length === 0 ? (
            <p className="muted">No updates linked to this project yet.</p>
          ) : (
            updates.map((update) => (
              <article key={update.id}>
                <strong>
                  {update.kind} by {update.author.name}
                </strong>
                <p>{update.body}</p>
                <p className="muted">{formatDate(update.created_at)}</p>
              </article>
            ))
          )}
        </section>
      </div>
    );
  } catch {
    notFound();
  }
}
