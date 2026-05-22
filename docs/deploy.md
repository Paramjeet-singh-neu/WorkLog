# Worklog Production Deploy

This deploy uses Render for the Python API + Discord bot worker, Vercel for the Next.js web app, and Neon Postgres for data.

## Quick checklist

1. Push latest code to GitHub.
2. Run production migrations: `alembic upgrade head` (uses `DATABASE_URL` from `.env`).
3. Deploy Render Blueprint (`render.yaml`) and paste env vars.
4. Deploy Vercel (`web/`) and paste env vars.
5. Set `PUBLIC_BASE_URL` on Render API to the Render API URL.
6. Set `WORKLOG_API_URL` on Vercel to the same Render API URL.
7. Add the Vercel OAuth callback URL in the Discord Developer Portal.
8. Restart the Render bot worker after env changes.
9. Smoke-test `/health`, web login, and `/skills` in Discord.

Generate a masked local env checklist:

```bash
source .venv/bin/activate
python scripts/generate_deploy_env.py
```

## Render

1. Push the repo to GitHub.
2. In Render, open **New → Blueprint** and connect `Paramjeet-singh-neu/WorkLog`.
3. Add these env vars to **both** services unless noted:
   - `DATABASE_URL`
   - `EMBEDDING_PROVIDER`
   - `EMBEDDING_DIMENSIONS`
   - `GEMINI_API_KEY` or `OPENAI_API_KEY`
   - `GEMINI_EMBEDDING_MODEL` or `OPENAI_EMBEDDING_MODEL`
4. Add these to the **API** service:
   - `DIGEST_TRIGGER_TOKEN`
   - `DISCORD_TOKEN`
   - `WORKLOG_CHANNEL_ID`
   - `DIGEST_CHANNEL_ID` (optional, defaults to `WORKLOG_CHANNEL_ID`)
   - `EMBEDDING_PROVIDER` (`gemini` or `openai`)
   - `GEMINI_API_KEY` or `OPENAI_API_KEY`
   - `PUBLIC_BASE_URL=https://worklog-api.onrender.com` (your actual Render URL)
5. Add these to the **bot worker**:
   - `DISCORD_TOKEN`
   - `DISCORD_GUILD_ID`
   - `WORKLOG_CHANNEL_ID`
   - `REVIEW_CHANNEL_ID`
   - `DIGEST_CHANNEL_ID` (optional)
   - `DIGEST_POST_HOUR_UTC=14`

Run migrations against production before first traffic:

```bash
alembic upgrade head
```

The bot posts the weekly digest on Mondays at `DIGEST_POST_HOUR_UTC` and records the run in `digest_runs` to avoid duplicate posts.

## Vercel

1. Import the repo at https://vercel.com/new.
2. Set the project root to `web`.
3. Or from CLI after `npx vercel login`:

```bash
cd web
npx vercel --prod
```
3. Add env vars:
   - `WORKLOG_API_URL=https://your-render-api.onrender.com`
   - `WEB_AUTH_SECRET`
   - `DISCORD_CLIENT_ID`
   - `DISCORD_CLIENT_SECRET`
   - `DISCORD_REDIRECT_URI=https://your-vercel-domain.vercel.app/api/auth/callback/discord`
   - `DIGEST_TRIGGER_TOKEN` (optional, enables `/admin`)
4. In Discord Developer Portal, add the Vercel callback URL exactly.

## Smoke Test

```bash
curl https://your-render-api.onrender.com/health
curl -H "Authorization: Bearer $DIGEST_TRIGGER_TOKEN" \
  https://your-render-api.onrender.com/digest/preview
```

Then test:

- `/skills`
- `/post progress`
- `/post blocked`
- `/follow user`
- `/follow project`
- `/kudos`
- Web login, ranked feed, project follow, comments, showcase, admin summary
