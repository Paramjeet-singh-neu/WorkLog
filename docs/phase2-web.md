# Worklog Phase 2 Web Viewer

Phase 2 is intentionally read-only. Discord remains the place where members write updates.

The web app provides:

- Chronological feed at `/`
- Discord OAuth login
- Current user's profile at `/profile`
- Project detail pages at `/projects/[id]`

## Required Local Setup

Start the Python API first:

```bash
source .venv/bin/activate
uvicorn api.main:app --reload
```

Then configure the web app:

```bash
cd web
cp .env.example .env.local
```

Fill `web/.env.local`:

```bash
WORKLOG_API_URL=http://127.0.0.1:8000
WEB_AUTH_SECRET=generate-a-long-random-string
DISCORD_CLIENT_ID=your-discord-application-id
DISCORD_CLIENT_SECRET=your-discord-client-secret
DISCORD_REDIRECT_URI=http://localhost:3000/api/auth/callback/discord
```

Generate `WEB_AUTH_SECRET`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Discord OAuth Setup

In the Discord Developer Portal:

1. Open the same Discord application used by the bot.
2. Go to **OAuth2**.
3. Copy **Client ID** into `DISCORD_CLIENT_ID`.
4. Reset or copy **Client Secret** into `DISCORD_CLIENT_SECRET`.
5. Under **Redirects**, add **both** of these URLs exactly (Discord requires an exact match):

```text
http://localhost:3000/api/auth/callback/discord
http://127.0.0.1:3000/api/auth/callback/discord
```

If you only add one, always open the site using that same host (`localhost` vs `127.0.0.1` are different to Discord).

6. Click **Save Changes** in the Developer Portal.

For Vercel, add the deployed callback too:

```text
https://your-vercel-domain.vercel.app/api/auth/callback/discord
```

## Run Locally

```bash
cd web
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Notes

- If `/profile` says no Worklog profile exists, use `/skills` or `/post progress` in Discord first.
- Project pages only show data once project rows exist. Phase 1 does not yet create projects.
- All writes still happen through Discord.
