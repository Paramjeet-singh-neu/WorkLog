# Worklog Phase 4 — Social Feedback

Phase 4 adds comments and kudos on updates. Discord stays a write path; the web adds read + interact when logged in.

## What ships

- **Tables**: `comments`, `kudos` (one kudo per user per update)
- **API**:
  - `GET /social?update_ids=1,2&viewer_discord_id=<id>` — batch comments + kudo counts
  - `GET /updates/{id}/social` — social for one update
  - `GET /updates/{id}` — single update with author/project
  - `POST /updates/{id}/comments?author_discord_id=<id>` — body `{ "body": "..." }`
  - `POST /updates/{id}/kudos?user_discord_id=<id>` — toggle kudo, returns `{ "added": true, "kudo_count": 3 }`
- **Discord**:
  - Reply to a Worklog embed message in `#worklog` or `#worklog-reviews` → saved as a comment
  - `/kudos update_id:<id>` — toggle kudo (update ID shown on the web feed)
  - `/follow project project_id:<id>` — toggle project follow
- **Web**: kudos button + comment form on feed cards; `/updates/[id]` thread page
  - Project pages include follow buttons
  - `/showcase` lists projects and momentum
  - `/admin` shows protected cohort health stats

## Discord setup

Enable **Message Content Intent** for the bot in the Discord Developer Portal (Bot → Privileged Gateway Intents). Required for reply-to-comment.

Restart the bot after changing intents:

```bash
source .venv/bin/activate
python -m bot.main
```

## Local verification

```bash
alembic upgrade head
uvicorn api.main:app --reload
```

```bash
curl "http://127.0.0.1:8000/social?update_ids=1,2"
curl -X POST "http://127.0.0.1:8000/updates/1/comments?author_discord_id=YOUR_ID" \
  -H "Content-Type: application/json" \
  -d '{"body":"Nice progress"}'
curl -X POST "http://127.0.0.1:8000/updates/1/kudos?user_discord_id=YOUR_ID"
```

Web: log in at http://localhost:3000, use **Give kudos** or **Comment** on a feed card.

## Notes

- Commenting via Discord only works when replying to the bot’s embed message (not arbitrary chat).
- Update authors get a DM when someone comments (Discord reply) or gives kudos (`/kudos` or web).
