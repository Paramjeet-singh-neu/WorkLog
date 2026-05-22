# Worklog Phase 5 — Digest, Follows, Showcase, Deploy

Phase 5 completes the remaining product surfaces after ranked feed and social feedback.

## What ships

### Weekly digest (Discord)

- `POST /digest/trigger` — posts the digest to Discord (uses `DIGEST_CHANNEL_ID` or `WORKLOG_CHANNEL_ID`)
- `GET /digest/preview` — preview only, same auth as trigger
- Bot **scheduled task**: Mondays at `DIGEST_POST_HOUR_UTC` (default 14 UTC), deduped via `digest_runs` table

### Project follows

- `GET /projects/{id}/social` — follower count + whether viewer follows
- `POST /projects/{id}/follow?viewer_discord_id=...` — toggle follow
- Discord: `/follow project project_id:<id>`
- Web: **Follow project** button on `/projects/[id]`

### Showcase & admin

- `GET /showcase` — public project cards with update/shipped/follower stats
- `GET /admin/summary` — protected cohort metrics (Bearer `DIGEST_TRIGGER_TOKEN`)
- Web: `/showcase`, `/admin` (admin needs `DIGEST_TRIGGER_TOKEN` in `web/.env.local`)

### Deploy

See `docs/deploy.md` for Render (API + bot) and Vercel (web).

## Env (new / important)

Root `.env`:

```bash
DIGEST_CHANNEL_ID=          # optional; defaults to WORKLOG_CHANNEL_ID
DIGEST_POST_HOUR_UTC=14     # Monday digest hour (UTC)
```

`web/.env.local` (optional for admin page):

```bash
DIGEST_TRIGGER_TOKEN=       # same as API, for /admin
```

## Quick tests

```bash
# Preview digest (no Discord post)
curl -H "Authorization: Bearer $DIGEST_TRIGGER_TOKEN" \
  http://127.0.0.1:8000/digest/preview

# Post digest to Discord
curl -X POST -H "Authorization: Bearer $DIGEST_TRIGGER_TOKEN" \
  http://127.0.0.1:8000/digest/trigger

curl http://127.0.0.1:8000/showcase
```

Discord:

```text
/follow project project_id:1
```

Web: http://localhost:3000/showcase and http://localhost:3000/admin

## Notes

- **AI summaries**: Phase 5 uses **rules-based** weekly digest text (counts + recent updates), not an LLM. Full AI-generated cohort summaries can be a later phase.
- **Projects in showcase**: rows appear once `projects` exist in the DB (Phase 1 does not auto-create projects from Discord posts yet).
- Restart the **bot** after deploy so `/follow project` and the Monday digest task load.
