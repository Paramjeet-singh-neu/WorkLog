# Worklog Phase 3 — Ranked Feed

Phase 3 adds a rules-based ranked feed for logged-in web users. Discord remains the write path.

## What ships

- **Ranking engine** (`api/feed.py`): scores recent updates per viewer
- **Tables**: `feed_cache` (5-minute Postgres cache per viewer), `feed_seen` (down-rank already viewed), `project_follows` (optional +25 when following a project)
- **API**:
  - `GET /feed?viewer_discord_id=<id>&limit=50` — ranked list
  - `POST /feed/seen?viewer_discord_id=<id>` — body `{ "update_ids": [1, 2] }`
- **Web**: logged-in home uses ranked feed; anonymous users see chronological `/updates`

## Scoring (MVP rules)

| Signal | Effect |
|--------|--------|
| Kind: blocked | +50 |
| Kind: seeking_review | +40 |
| Kind: shipped | +20 |
| Kind: progress | +10 |
| Author in `/follow` list | +30 |
| Project in `project_follows` | +25 |
| Blocker body similar to viewer skills (cosine distance ≤ 0.45) | +35 |
| Time decay | × 0.95^hours since post |
| Already seen on web | × 0.3 |

Results are sorted by score descending. Cache refreshes every 5 minutes per viewer.

## Local verification

1. Apply migration:

```bash
source .venv/bin/activate
alembic upgrade head
```

2. Restart API:

```bash
uvicorn api.main:app --reload
```

3. Seed data from Discord (`/skills`, `/post`, `/follow`) with two accounts if possible.

4. API checks:

```bash
curl "http://127.0.0.1:8000/feed?viewer_discord_id=YOUR_DISCORD_ID"
curl -X POST "http://127.0.0.1:8000/feed/seen?viewer_discord_id=YOUR_DISCORD_ID" \
  -H "Content-Type: application/json" \
  -d '{"update_ids":[1]}'
```

5. Web: log in at `http://localhost:3000` — header should show **Ranked for you**. Log out to see chronological public feed.

## Notes

- `project_follows` is wired in ranking but not yet exposed as a Discord command; insert rows manually or add `/follow project` later.
- Blocker skill-match bonus uses the same embedding provider as the bot (`EMBEDDING_PROVIDER` in `.env`).
- Viewing the home feed marks visible update IDs as seen (affects future ranking).
