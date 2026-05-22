"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { UpdateSocial } from "@/lib/types";

type Props = {
  updateId: number;
  initial: UpdateSocial;
  canInteract: boolean;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function UpdateSocialPanel({ updateId, initial, canInteract }: Props) {
  const router = useRouter();
  const [social, setSocial] = useState(initial);
  const [commentBody, setCommentBody] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggleKudo() {
    setPending(true);
    setError(null);
    try {
      const response = await fetch(`/api/updates/${updateId}/kudo`, { method: "POST" });
      if (!response.ok) {
        throw new Error("Could not update kudos");
      }
      const data = (await response.json()) as { added: boolean; kudo_count: number };
      setSocial((current) => ({
        ...current,
        kudo_count: data.kudo_count,
        viewer_has_kudo: data.added,
      }));
      router.refresh();
    } catch {
      setError("Could not update kudos. Try again.");
    } finally {
      setPending(false);
    }
  }

  async function submitComment(event: React.FormEvent) {
    event.preventDefault();
    const body = commentBody.trim();
    if (!body) {
      return;
    }

    setPending(true);
    setError(null);
    try {
      const response = await fetch(`/api/updates/${updateId}/comment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body }),
      });
      if (!response.ok) {
        throw new Error("Could not post comment");
      }
      const comment = (await response.json()) as UpdateSocial["comments"][number];
      setSocial((current) => ({
        ...current,
        comments: [...current.comments, comment],
      }));
      setCommentBody("");
      router.refresh();
    } catch {
      setError("Could not post comment. Try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="social-panel">
      <div className="social-actions">
        <button
          type="button"
          className={`kudo-button${social.viewer_has_kudo ? " active" : ""}`}
          disabled={!canInteract || pending}
          onClick={() => void toggleKudo()}
        >
          {social.viewer_has_kudo ? "Kudos given" : "Give kudos"} · {social.kudo_count}
        </button>
        {!canInteract ? (
          <span className="muted">Log in to give kudos or comment on the web.</span>
        ) : null}
      </div>

      {social.comments.length > 0 ? (
        <ul className="comment-list">
          {social.comments.map((comment) => (
            <li key={comment.id}>
              <strong>{comment.author.name}</strong>
              <span className="muted"> · {formatDate(comment.created_at)}</span>
              <p>{comment.body}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No comments yet. Reply to the Discord post or comment here.</p>
      )}

      {canInteract ? (
        <form className="comment-form" onSubmit={(event) => void submitComment(event)}>
          <textarea
            value={commentBody}
            onChange={(event) => setCommentBody(event.target.value)}
            placeholder="Add a comment..."
            rows={3}
            maxLength={2000}
            disabled={pending}
          />
          <button type="submit" className="button" disabled={pending || !commentBody.trim()}>
            Comment
          </button>
        </form>
      ) : null}

      {error ? <p className="error-text">{error}</p> : null}
    </div>
  );
}
