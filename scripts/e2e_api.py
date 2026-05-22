#!/usr/bin/env python3
"""Automated API end-to-end checks for Worklog."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.config import get_settings  # noqa: E402


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def ok(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"[PASS] {label}{suffix}")


def fail(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"[FAIL] {label}{suffix}")
    raise SystemExit(1)


async def main() -> None:
    load_dotenv()
    settings = get_settings()
    base = settings.public_base_url.rstrip("/")
    token = settings.digest_trigger_token or ""
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        health = await client.get(f"{base}/health")
        if health.status_code != 200:
            fail("GET /health", str(health.status_code))
        ok("GET /health")

        updates = await client.get(f"{base}/updates?limit=10")
        if updates.status_code != 200:
            fail("GET /updates", str(updates.status_code))
        update_list = updates.json()
        ok("GET /updates", f"{len(update_list)} items")
        if not update_list:
            fail("seed data", "no updates in database — post from Discord first")
        update_id = update_list[0]["id"]

        viewer = await client.get(f"{base}/users/discord/1386084416404848841")
        if viewer.status_code != 200:
            fail("GET /users/discord/{id}", str(viewer.status_code))
        viewer_discord_id = viewer.json()["discord_id"]
        ok("GET /users/discord/{id}", viewer.json()["name"])

        feed = await client.get(
            f"{base}/feed",
            params={"viewer_discord_id": viewer_discord_id, "limit": 10},
        )
        if feed.status_code != 200:
            fail("GET /feed", str(feed.status_code))
        ok("GET /feed (ranked)", f"{len(feed.json())} items")

        social = await client.get(
            f"{base}/social",
            params={"update_ids": str(update_id), "viewer_discord_id": viewer_discord_id},
        )
        if social.status_code != 200:
            fail("GET /social", str(social.status_code))
        ok("GET /social")

        comment = await client.post(
            f"{base}/updates/{update_id}/comments",
            params={"author_discord_id": viewer_discord_id},
            json={"body": "E2E automated comment"},
        )
        if comment.status_code != 200:
            fail("POST /updates/{id}/comments", str(comment.status_code))
        ok("POST comment")

        kudo = await client.post(
            f"{base}/updates/{update_id}/kudos",
            params={"user_discord_id": viewer_discord_id},
        )
        if kudo.status_code != 200:
            fail("POST /updates/{id}/kudos", str(kudo.status_code))
        kudo_data = kudo.json()
        ok("POST kudos toggle", f"added={kudo_data.get('added')}")

        seen = await client.post(
            f"{base}/feed/seen",
            params={"viewer_discord_id": viewer_discord_id},
            json={"update_ids": [update_id]},
        )
        if seen.status_code != 200:
            fail("POST /feed/seen", str(seen.status_code))
        ok("POST /feed/seen")

        preview = await client.get(f"{base}/digest/preview", headers=headers)
        if preview.status_code != 200:
            fail("GET /digest/preview", str(preview.status_code))
        ok("GET /digest/preview", f"{len(preview.json().get('message', ''))} chars")

        showcase = await client.get(f"{base}/showcase")
        if showcase.status_code != 200:
            fail("GET /showcase", str(showcase.status_code))
        ok("GET /showcase", f"{len(showcase.json())} projects")

        admin = await client.get(f"{base}/admin/summary", headers=headers)
        if admin.status_code != 200:
            fail("GET /admin/summary", str(admin.status_code))
        summary = admin.json()
        ok(
            "GET /admin/summary",
            f"users={summary['users']} updates={summary['updates']} kudos={summary['kudos']}",
        )

        detail = await client.get(f"{base}/updates/{update_id}")
        if detail.status_code != 200:
            fail("GET /updates/{id}", str(detail.status_code))
        ok("GET /updates/{id}")

    print("\nAll automated API E2E checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
