import Link from "next/link";
import { UpdateSocialPanel } from "@/components/UpdateSocialPanel";
import { getBatchSocial, getFeed, getRankedFeed, markFeedSeen } from "@/lib/api";
import { getSession } from "@/lib/session";
import type { Update, UpdateSocial } from "@/lib/types";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function updateLabel(kind: Update["kind"]) {
  return kind === "seeking_review" ? "review" : kind;
}

function emptySocial(updateId: number): UpdateSocial {
  return {
    update_id: updateId,
    comments: [],
    kudo_count: 0,
    viewer_has_kudo: false,
  };
}

export default async function FeedPage() {
  const session = await getSession();
  let ranked = false;
  let updates: Update[];

  if (session) {
    ranked = true;
    updates = await getRankedFeed(session.id);
    if (updates.length > 0) {
      await markFeedSeen(
        session.id,
        updates.map((update) => update.id),
      );
    }
  } else {
    updates = await getFeed();
  }

  const socialByUpdate =
    updates.length > 0
      ? await getBatchSocial(
          updates.map((update) => update.id),
          session?.id,
        )
      : {};

  return (
    <div className="stack">
      <section className="card">
        <p className="pill">{ranked ? "Ranked for you" : "Public feed"}</p>
        <h1>{ranked ? "Your cohort feed" : "Chronological cohort feed"}</h1>
        <p className="muted">
          Writes still happen in Discord.{" "}
          {ranked
            ? "Updates are ranked by kind, who you follow, skill match on blockers, and recency."
            : "Log in to see a feed ranked for you."}{" "}
          Reply to a Worklog post in Discord to comment, or use kudos and comments here.
        </p>
        {!session ? (
          <p>
            <a className="button" href="/api/auth/login">
              Log in with Discord
            </a>
          </p>
        ) : (
          <p className="muted">Logged in as {session.username}.</p>
        )}
      </section>

      {updates.length === 0 ? (
        <section className="card">
          <p className="muted">No updates yet. Post from Discord to fill this feed.</p>
        </section>
      ) : (
        updates.map((update) => (
          <article className="card stack" key={update.id}>
            <div>
              <span className="pill">{updateLabel(update.kind)}</span>
              <h2>{update.author.name}</h2>
              <p className="muted">{formatDate(update.created_at)}</p>
            </div>
            <p>{update.body}</p>
            <p className="muted">
              Update #{update.id} · <Link href={`/updates/${update.id}`}>Open thread</Link>
            </p>
            {update.project ? (
              <Link href={`/projects/${update.project.id}`}>View project: {update.project.title}</Link>
            ) : null}
            <UpdateSocialPanel
              updateId={update.id}
              initial={socialByUpdate[update.id] ?? emptySocial(update.id)}
              canInteract={Boolean(session)}
            />
          </article>
        ))
      )}
    </div>
  );
}
