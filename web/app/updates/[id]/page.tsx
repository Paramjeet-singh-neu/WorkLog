import Link from "next/link";
import { notFound } from "next/navigation";
import { UpdateSocialPanel } from "@/components/UpdateSocialPanel";
import { getUpdate, getUpdateSocial } from "@/lib/api";
import { getSession } from "@/lib/session";
import type { Update } from "@/lib/types";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function updateLabel(kind: Update["kind"]) {
  return kind === "seeking_review" ? "review" : kind;
}

export default async function UpdateDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const updateId = Number(id);
  if (!Number.isFinite(updateId)) {
    notFound();
  }

  const session = await getSession();
  let update;
  try {
    update = await getUpdate(updateId);
  } catch {
    notFound();
  }

  const social = await getUpdateSocial(updateId, session?.id);

  return (
    <div className="stack">
      <section className="card">
        <Link href="/" className="muted">
          ← Back to feed
        </Link>
        <p className="pill">{updateLabel(update.kind)}</p>
        <h1>{update.author.name}</h1>
        <p className="muted">{formatDate(update.created_at)}</p>
        <p>{update.body}</p>
        <p className="muted">Update #{update.id}</p>
      </section>

      <section className="card stack">
        <h2>Discussion</h2>
        <UpdateSocialPanel
          updateId={update.id}
          initial={social}
          canInteract={Boolean(session)}
        />
      </section>
    </div>
  );
}
