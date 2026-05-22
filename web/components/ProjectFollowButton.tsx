"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { ProjectSocial } from "@/lib/types";

type Props = {
  projectId: number;
  initial: ProjectSocial;
  canInteract: boolean;
};

export function ProjectFollowButton({ projectId, initial, canInteract }: Props) {
  const router = useRouter();
  const [social, setSocial] = useState(initial);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggleFollow() {
    setPending(true);
    setError(null);
    try {
      const response = await fetch(`/api/projects/${projectId}/follow`, { method: "POST" });
      if (!response.ok) {
        throw new Error("Could not update follow");
      }
      const data = (await response.json()) as { following: boolean; follower_count: number };
      setSocial((current) => ({
        ...current,
        follower_count: data.follower_count,
        viewer_following: data.following,
      }));
      router.refresh();
    } catch {
      setError("Could not update project follow. Try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="social-actions">
      <button
        type="button"
        className={`kudo-button${social.viewer_following ? " active" : ""}`}
        disabled={!canInteract || pending}
        onClick={() => void toggleFollow()}
      >
        {social.viewer_following ? "Following project" : "Follow project"} ·{" "}
        {social.follower_count}
      </button>
      {!canInteract ? <span className="muted">Log in to follow this project.</span> : null}
      {error ? <p className="error-text">{error}</p> : null}
    </div>
  );
}
