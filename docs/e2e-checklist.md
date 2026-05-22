# Worklog E2E Checklist

Use this checklist before demoing or submitting the project.

## 1. Start Local Services

Run each service in a separate terminal:

```bash
source .venv/bin/activate
uvicorn api.main:app --reload
```

```bash
source .venv/bin/activate
python -m bot.main
```

```bash
npm --prefix web run dev
```

Open the web app at:

```text
http://localhost:3000
```

## 2. Automated Checks

```bash
source .venv/bin/activate
alembic upgrade head
python scripts/doctor.py
python scripts/e2e_api.py
npm --prefix web run typecheck
npm --prefix web run build
```

Expected result: all commands complete successfully.

## 3. Discord Bot Checks

In your Discord test server:

1. Run `/skills python, fastapi, postgres, pgvector`.
2. Run `/post progress Testing Worklog E2E from Discord`.
3. Run `/post shipped Finished Worklog E2E smoke test`.
4. Run `/post blocked Stuck on pgvector similarity search`.
5. Run `/post review https://github.com/Paramjeet-singh-neu/WorkLog`.
6. Confirm progress, shipped, and blocked updates appear in the worklog channel.
7. Confirm the review request appears in the review channel.
8. Confirm a matching helper receives a DM for the blocked update.
9. Run `/me` and confirm the bot sends you a profile/activity DM.
10. Run `/follow user @someone` and confirm the command toggles the follow state.
11. Run `/follow project project_id:1` and confirm the command toggles the project follow state.

If `/follow project` does not appear in Discord:

1. Stop all local bot processes (`Ctrl+C` in every terminal running `python -m bot.main`).
2. Force-sync slash commands to your test guild:

```bash
source .venv/bin/activate
python scripts/sync_discord_commands.py
```

3. Confirm the script output includes:

```text
/follow -> user, project
```

4. Start the bot again:

```bash
python -m bot.main
```

5. In Discord, type `/follow` and select the **project** subcommand from the autocomplete list.
6. Enter `1` into the `project_id` field.
7. If it still does not show, fully quit and reopen Discord or test from the Discord mobile app/browser to clear the client command cache.

For Discord reply comments, enable **Message Content Intent** in the Discord Developer Portal:

1. Open <https://discord.com/developers/applications>.
2. Select the same application used by your Worklog bot.
3. Open **Bot** in the left sidebar.
4. Scroll to **Privileged Gateway Intents**.
5. Enable **Message Content Intent**.
6. Click **Save Changes**.
7. Restart the local bot:

```bash
source .venv/bin/activate
python -m bot.main
```

8. Reply directly to a Worklog embed in the worklog channel.
9. Open the matching update page in the web UI, for example `http://localhost:3000/updates/UPDATE_ID`.
10. Confirm the Discord reply appears as a comment.

## 4. Social Feedback Checks

Find an update ID from the web feed or API, then:

```bash
curl http://127.0.0.1:8000/updates/UPDATE_ID
curl http://127.0.0.1:8000/updates/UPDATE_ID/social
```

In Discord:

```text
/kudos update_id:UPDATE_ID
```

On the web:

1. Open `http://localhost:3000/updates/UPDATE_ID`.
2. Click the kudos button.
3. Add a comment.
4. Refresh and confirm the counts/comments persist.

## 5. Feed And Web Checks

1. Visit `http://localhost:3000` while logged out and confirm the public feed loads.
2. Log in with Discord and confirm the homepage says it is ranked for you.
3. Visit `http://localhost:3000/profile` and confirm your Worklog profile loads.
4. Visit `http://localhost:3000/showcase` and confirm projects render.
5. Visit `http://localhost:3000/admin` and confirm the summary loads if `DIGEST_TRIGGER_TOKEN` is set in `web/.env.local`.

## 6. Project Follow And Showcase Checks

Project follow requires at least one row in the `projects` table. If no projects exist yet, create one locally or seed one for demo data.

After you have a project ID:

```bash
VIEWER_DISCORD_ID=your_discord_id
PROJECT_ID=1

curl "http://127.0.0.1:8000/projects/$PROJECT_ID/social?viewer_discord_id=$VIEWER_DISCORD_ID"
curl -X POST "http://127.0.0.1:8000/projects/$PROJECT_ID/follow?viewer_discord_id=$VIEWER_DISCORD_ID"
curl http://127.0.0.1:8000/showcase
```

On the web:

1. Open `http://localhost:3000/projects/PROJECT_ID`.
2. Click **Follow project**.
3. Refresh and confirm the follower count/state persists.

In Discord:

```text
/follow project project_id:PROJECT_ID
```

## 7. Digest Checks

Preview without posting:

```bash
curl -H "Authorization: Bearer $DIGEST_TRIGGER_TOKEN" \
  http://127.0.0.1:8000/digest/preview
```

Post to Discord:

```bash
curl -X POST -H "Authorization: Bearer $DIGEST_TRIGGER_TOKEN" \
  http://127.0.0.1:8000/digest/trigger
```

Expected result: the preview returns digest text, and the trigger posts that digest to `DIGEST_CHANNEL_ID` or `WORKLOG_CHANNEL_ID`.

## 8. Submission Readiness

Before submitting:

1. Confirm `.env` and `web/.env.local` are not committed.
2. Confirm `README.md` includes setup, architecture, testing, and deployment notes.
3. Confirm the latest commit is pushed to GitHub.
4. Share the GitHub repo URL and, if deployed, the Render/Vercel URLs.
