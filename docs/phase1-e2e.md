# Worklog Phase 1 Setup and End-to-End Test Guide

This guide takes you from an empty local checkout to a working Phase 1 Discord bot test.

Phase 1 includes:

- `/skills`
- `/post shipped`
- `/post progress`
- `/post blocked`
- `/post review`
- `/follow`
- `/me`
- API `GET /health`
- API `POST /digest/trigger`
- Postgres persistence for users, updates, follows, and blocker matches

## What You Need

You need these accounts and services:

- Discord account
- A Discord test server where you are admin
- OpenAI API key or Gemini API key
- Neon Postgres database
- Python 3.11 or newer

Optional for deployment testing:

- Render account
- UptimeRobot account

## Step 1: Create a Discord Test Server

Do this from your Discord app:

1. Click the plus button in the server list.
2. Choose **Create My Own**.
3. Choose **For me and my friends**.
4. Name it something like `Worklog Test`.
5. Create two text channels:
   - `#worklog`
   - `#worklog-reviews`

Keep this as a private test server until the bot works.

## Step 2: Create the Discord Bot

Do this in the Discord Developer Portal:

1. Go to <https://discord.com/developers/applications>.
2. Click **New Application**.
3. Name it `Worklog Dev`.
4. Open the application.
5. Go to **Bot**.
6. Click **Add Bot** if Discord has not created one yet.
7. Under **Token**, click **Reset Token** or **View Token**.
8. Save that token for `DISCORD_TOKEN`.

Important: do not commit this token to git.

## Step 3: Invite the Bot to Your Test Server

In the Discord Developer Portal:

1. Open your application.
2. Go to **OAuth2**.
3. Go to **URL Generator**.
4. Under **Scopes**, select:
   - `bot`
   - `applications.commands`
5. Under **Bot Permissions**, select:
   - View Channels
   - Send Messages
   - Embed Links
   - Read Message History
   - Create Public Threads
   - Send Messages in Threads
6. Copy the generated URL.
7. Open it in your browser.
8. Invite the bot to your `Worklog Test` server.

## Step 4: Copy Discord IDs

You need numeric IDs for your guild and channels.

In Discord:

1. Open **User Settings**.
2. Go to **Advanced**.
3. Turn on **Developer Mode**.
4. Right-click your test server name and click **Copy Server ID**.
   - This is `DISCORD_GUILD_ID`.
5. Right-click `#worklog` and click **Copy Channel ID**.
   - This is `WORKLOG_CHANNEL_ID`.
6. Right-click `#worklog-reviews` and click **Copy Channel ID**.
   - This is `REVIEW_CHANNEL_ID`.

## Step 5: Create Neon Postgres

Do this in Neon:

1. Go to <https://neon.tech>.
2. Create a new project.
3. Copy the connection string.
4. Use the pooled or direct URL. Either is fine for this MVP.
5. Save it as `DATABASE_URL`.

The app accepts both:

```bash
postgresql://...
postgresql+asyncpg://...
```

The code normalizes the URL automatically.

## Step 6: Create an Embedding API Key

Worklog needs one embedding provider for `/skills` and `/post blocked`.

Option A, Gemini:

1. Go to <https://aistudio.google.com/app/apikey>.
2. Create a Gemini API key.
3. Save it as `GEMINI_API_KEY`.
4. Set `EMBEDDING_PROVIDER=gemini`.

Option B, OpenAI:

1. Go to <https://platform.openai.com/api-keys>.
2. Create a new key.
3. Save it as `OPENAI_API_KEY`.
4. Set `EMBEDDING_PROVIDER=openai`.

This is required for:

- `/skills`
- `/post blocked`

The app uses 1536-dimensional vectors by default because the database migration creates
`Vector(1536)`. Keep `EMBEDDING_DIMENSIONS=1536` unless you also change the migration.

## Step 7: Create Your Local `.env`

From the project root:

```bash
cp .env.example .env
```

Fill it like this:

```bash
DATABASE_URL=postgresql://your-neon-url
DISCORD_TOKEN=your-discord-bot-token
DISCORD_GUILD_ID=your-test-server-id
WORKLOG_CHANNEL_ID=your-worklog-channel-id
REVIEW_CHANNEL_ID=your-review-channel-id
EMBEDDING_PROVIDER=gemini
EMBEDDING_DIMENSIONS=1536
OPENAI_API_KEY=your-openai-api-key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
GEMINI_API_KEY=your-gemini-api-key
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
DIGEST_TRIGGER_TOKEN=make-up-a-long-random-secret
PUBLIC_BASE_URL=http://localhost:8000
```

## Step 8: Install Dependencies

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If `python3` fails, install Python 3.11+ first.

## Step 9: Run the Local Doctor

After `.env` is filled and dependencies are installed:

```bash
python3 scripts/doctor.py
```

The doctor checks:

- Python version
- Required env vars
- Whether key dependencies import
- Database connectivity
- Whether `pgvector` exists
- API health if the API is running

If you only want local checks without network calls:

```bash
python3 scripts/doctor.py --no-network
```

## Step 10: Run Migrations

With the virtual environment active:

```bash
alembic upgrade head
```

This creates:

- `users`
- `projects`
- `updates`
- `follows`
- `matches`
- Postgres enum types
- `pgvector` extension

## Step 11: Start the API

Open terminal 1:

```bash
source .venv/bin/activate
uvicorn api.main:app --reload
```

Then test:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"ok":"true"}
```

Test the protected digest trigger:

```bash
curl -X POST http://localhost:8000/digest/trigger \
  -H "Authorization: Bearer your-digest-token"
```

Expected response:

```json
{"ok":true,"message":"No Worklog updates yet."}
```

## Step 12: Start the Bot

Open terminal 2:

```bash
source .venv/bin/activate
python -m bot.main
```

The bot should come online in your Discord test server.

Because `DISCORD_GUILD_ID` is set, slash commands should appear quickly. If they do not:

1. Wait 30 seconds.
2. Restart the bot.
3. Check that the bot was invited with `applications.commands`.

## Step 13: Prepare Test Users

For a real end-to-end test, use at least three Discord users.

Recommended:

- User A: blocker author
- User B: helper with backend skills
- User C: helper with frontend skills
- Optional User D: follower

Make sure server DMs are enabled for these accounts:

1. Right-click the server.
2. Open **Privacy Settings**.
3. Enable direct messages from server members.

## Step 14: Test `/skills`

As User B:

```text
/skills python, fastapi, postgres, sqlalchemy
```

As User C:

```text
/skills react, nextjs, typescript, css
```

Expected:

- Discord shows an ephemeral success message.
- The `users` table has rows for both users.
- `skills_embedding` is not null for both users.

Optional SQL check in Neon:

```sql
select name, skills_text, skills_embedding is not null as has_embedding
from users;
```

## Step 15: Test Normal Updates

As User A:

```text
/post progress Building the first Worklog test flow
```

Expected:

- Embed appears in `#worklog`.
- `updates.kind` is `progress`.

Then:

```text
/post shipped First Discord update posted successfully
```

Expected:

- Embed appears in `#worklog`.
- `updates.kind` is `shipped`.

SQL check:

```sql
select kind, body, discord_message_id
from updates
order by created_at desc;
```

## Step 16: Test Review Requests

As User A:

```text
/post review https://github.com/example/example/pull/1
```

Expected:

- Embed appears in `#worklog-reviews`.
- `updates.kind` is `seeking_review`.

## Step 17: Test Follow Notifications

As User D:

```text
/follow @UserA
```

Then as User A:

```text
/post progress Testing follower DMs
```

Expected:

- User D receives a DM with a jump link.
- `follows` table has one row.

SQL check:

```sql
select * from follows;
```

## Step 18: Test Blocker Routing

As User A:

```text
/post blocked Stuck on SQLAlchemy and pgvector similarity search
```

Expected:

- Blocker embed appears in `#worklog`.
- User B should receive a DM because their skills mention backend/database terms.
- User A should not be matched to their own blocker.
- `matches` table gets rows.

SQL check:

```sql
select m.id, u.name, m.responded_at
from matches m
join users u on u.id = m.matched_user_id
order by m.created_at desc;
```

## Step 19: Test "I Can Help"

As the matched helper:

1. Open the bot DM.
2. Click **I can help**.

Expected:

- A thread is created on the blocker message in `#worklog`.
- The helper is added to the thread.
- A message is posted saying the helper can help.
- `matches.responded_at` becomes non-null.

SQL check:

```sql
select id, responded_at
from matches
order by created_at desc;
```

## Step 20: Test `/me`

As User A:

```text
/me
```

Expected:

- User A receives a DM with recent updates.

If it fails:

- Check that User A allows DMs from server members.

## Step 21: Test Digest Preview After Updates

Call:

```bash
curl -X POST http://localhost:8000/digest/trigger \
  -H "Authorization: Bearer your-digest-token"
```

Expected:

- The response contains recent updates.

This is only a preview in Phase 1. It does not post a Monday digest to Discord yet.

## Step 22: What Counts as Passing Phase 1 E2E

Phase 1 is passing when:

- The API health check works.
- Migrations run against Neon.
- The bot starts and slash commands sync.
- `/skills` creates user skill embeddings.
- `/post shipped`, `/post progress`, and `/post review` create Discord embeds and DB rows.
- `/follow` sends a DM on the next target-user post.
- `/post blocked` creates a blocker update, matches helpers, sends DMs, and records `matches`.
- Clicking **I can help** creates a thread and sets `responded_at`.
- `/me` sends the user a recent activity summary.

## Common Problems

### Slash commands do not show up

Check:

- `DISCORD_GUILD_ID` is correct.
- Bot was invited with `applications.commands`.
- Bot is running without startup errors.
- You restarted the bot after changing `.env`.

### Bot starts but cannot post

Check:

- `WORKLOG_CHANNEL_ID` is correct.
- `REVIEW_CHANNEL_ID` is correct.
- Bot role can view and send messages in both channels.

### Blocker DMs do not arrive

Check:

- Helpers ran `/skills` first.
- Helpers have DMs enabled.
- Helpers are not inside the 24-hour match cooldown.
- Your selected embedding key is valid.
- `skills_embedding` is not null in the database.

### "I can help" button fails

Check:

- Bot has `Create Public Threads`.
- Bot has `Send Messages in Threads`.
- Bot can fetch messages in `#worklog`.

### Migration fails creating vector extension

Check:

- You are using Neon Postgres.
- Your database user can create extensions.
- Run this manually in Neon SQL editor if needed:

```sql
create extension if not exists vector;
```

## Deploy Parity Check on Render

Only do this after local E2E passes.

1. Push this repo to GitHub.
2. In Render, create a Blueprint from `render.yaml`.
3. Add the same environment variables to both services where needed.
4. Run `alembic upgrade head` once from a Render shell or locally against the production Neon URL.
5. Confirm:
   - `worklog-api` responds to `/health`.
   - `worklog-bot` is online in Discord.
   - Slash commands work with the deployed bot.

Then add UptimeRobot:

1. Create an HTTP monitor.
2. URL: `https://your-render-api-url/health`
3. Interval: 14 minutes.
