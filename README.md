# Worklog

Discord-native work updates and blocker routing for project-building cohorts.

Worklog is built for the Cursor Boston wedge described in the project plan: keep cohort communication inside Discord, but turn shipped work, progress, blockers, and review requests into structured objects.

## Phase 1 MVP

Implemented now:

- `/skills <skills>` stores a member's skill profile and embeds it with OpenAI `text-embedding-3-small`.
- `/post shipped <message>` posts a shipped update embed to the Worklog channel.
- `/post progress <message>` posts a progress update embed to the Worklog channel.
- `/post blocked <message>` posts a blocker, finds skill-matched helpers, DMs the top matches, and tracks responses.
- `/post review <link>` posts a review request to the review channel.
- `/follow @user` subscribes to DM notifications when that member posts.
- `/me` DMs the caller a short summary of their recent activity.
- FastAPI exposes `/health` and a protected `/digest/trigger` preview endpoint.

Phase 3 adds a rules-based ranked web feed (`GET /feed`, `POST /feed/seen`) for logged-in users.

Phase 4 adds comments and kudos on updates (Discord replies, `/kudos`, and web interactions). See `docs/phase4-social.md`.

Phase 5 adds Discord-posted weekly digests, `/follow project`, web project follows, public showcase, and a lightweight admin summary.

Intentionally not implemented yet: full weekly digest automation, admin panels, and AI-generated summaries.

## Stack

- Python 3.11+
- `discord.py` bot worker
- FastAPI web service
- Neon Postgres with `pgvector`
- SQLAlchemy + Alembic
- OpenAI or Gemini embeddings for skill matching
- Next.js web viewer for Phase 2
- Render web service + background worker

## Setup

1. Create a Discord application and bot, then invite it to the server with slash-command and bot permissions.
2. Create two Discord channels, for example `#worklog` and `#worklog-reviews`.
3. Create a Neon Postgres database and enable `pgvector` through the migration.
4. Copy `.env.example` to `.env` and fill in the values.
5. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

6. Check your setup:

```bash
python3 scripts/doctor.py --no-network
```

7. Run migrations:

```bash
alembic upgrade head
```

8. Run the API locally:

```bash
uvicorn api.main:app --reload
```

9. Run the bot locally:

```bash
python -m bot.main
```

For the complete Discord + Neon + embedding-provider test walkthrough, see `docs/phase1-e2e.md`.
For the Phase 2 web viewer setup, see `docs/phase2-web.md`.
For Phase 3 ranked feed scoring and testing, see `docs/phase3-feed.md`.
For Phase 4 comments and kudos, see `docs/phase4-social.md`.
For Phase 5 digest, project follows, showcase, and deploy, see `docs/phase5-polish.md`.

## Environment Variables

- `DATABASE_URL`: Postgres URL from Neon. Both `postgresql://...` and `postgresql+asyncpg://...` work.
- `DISCORD_TOKEN`: Discord bot token.
- `DISCORD_GUILD_ID`: Optional guild ID for faster command sync during the MVP.
- `WORKLOG_CHANNEL_ID`: Channel where shipped/progress/blocked updates are posted.
- `REVIEW_CHANNEL_ID`: Channel where review requests are posted.
- `EMBEDDING_PROVIDER`: `openai` or `gemini`.
- `EMBEDDING_DIMENSIONS`: Defaults to `1536`, matching the current pgvector column.
- `OPENAI_API_KEY`: Required only when `EMBEDDING_PROVIDER=openai`.
- `OPENAI_EMBEDDING_MODEL`: Defaults to `text-embedding-3-small`.
- `GEMINI_API_KEY`: Required only when `EMBEDDING_PROVIDER=gemini`.
- `GEMINI_EMBEDDING_MODEL`: Defaults to `gemini-embedding-001`.
- `DIGEST_TRIGGER_TOKEN`: Bearer token for `POST /digest/trigger`.
- `DIGEST_CHANNEL_ID`: Optional Discord channel for weekly digests. Defaults to `WORKLOG_CHANNEL_ID`.
- `DIGEST_POST_HOUR_UTC`: Monday digest post hour in UTC. Defaults to `14`.
- `PUBLIC_BASE_URL`: Public API URL for deployed services.
- `WORKLOG_API_URL`: Web app URL for the FastAPI service.
- `WEB_AUTH_SECRET`: Long random secret used to sign the web session cookie.
- `DISCORD_CLIENT_ID`: Discord application client ID for OAuth.
- `DISCORD_CLIENT_SECRET`: Discord OAuth client secret.
- `DISCORD_REDIRECT_URI`: Discord OAuth callback URL.

## Deployment Notes

`render.yaml` defines two services:

- `worklog-api`: FastAPI web service.
- `worklog-bot`: Discord bot background worker.

Point UptimeRobot at `GET /health` on the API service if you want to keep the free web service warm.
For full Render/Vercel deployment steps, see `docs/deploy.md`.

## Product Guardrails

Phase 1 should stay Discord-only. Run it with a small cohort, watch whether unprompted posting and blocker-match responses happen, and only add Phase 2 web views after users explicitly ask for history or profile pages.
