#!/usr/bin/env python3
"""Print production env var checklists from local .env files (values masked)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def mask(value: str) -> str:
    if not value:
        return "(missing)"
    return "(set)"


def section(title: str, keys: list[str], values: dict[str, str]) -> None:
    print(f"\n## {title}\n")
    for key in keys:
        print(f"{key}={mask(values.get(key, ''))}")


def main() -> None:
    root_env = load_env(ROOT / ".env")
    web_env = load_env(ROOT / "web" / ".env.local")

    print("Worklog production env checklist")
    print("Copy real values from .env and web/.env.local into Render/Vercel dashboards.")
    print("Do not commit these files.\n")

    section(
        "Render — worklog-api",
        [
            "DATABASE_URL",
            "DISCORD_TOKEN",
            "WORKLOG_CHANNEL_ID",
            "DIGEST_CHANNEL_ID",
            "DIGEST_TRIGGER_TOKEN",
            "EMBEDDING_PROVIDER",
            "EMBEDDING_DIMENSIONS",
            "GEMINI_API_KEY",
            "GEMINI_EMBEDDING_MODEL",
            "OPENAI_API_KEY",
            "OPENAI_EMBEDDING_MODEL",
            "PUBLIC_BASE_URL",
        ],
        root_env,
    )
    print("PUBLIC_BASE_URL should be your Render API URL, e.g. https://worklog-api.onrender.com")

    section(
        "Render — worklog-bot",
        [
            "DATABASE_URL",
            "DISCORD_TOKEN",
            "DISCORD_GUILD_ID",
            "WORKLOG_CHANNEL_ID",
            "REVIEW_CHANNEL_ID",
            "DIGEST_CHANNEL_ID",
            "DIGEST_POST_HOUR_UTC",
            "EMBEDDING_PROVIDER",
            "EMBEDDING_DIMENSIONS",
            "GEMINI_API_KEY",
            "GEMINI_EMBEDDING_MODEL",
        ],
        root_env,
    )

    section(
        "Vercel — web",
        [
            "WORKLOG_API_URL",
            "WEB_AUTH_SECRET",
            "DISCORD_CLIENT_ID",
            "DISCORD_CLIENT_SECRET",
            "DISCORD_REDIRECT_URI",
            "DIGEST_TRIGGER_TOKEN",
        ],
        {**web_env, "DIGEST_TRIGGER_TOKEN": web_env.get("DIGEST_TRIGGER_TOKEN") or root_env.get("DIGEST_TRIGGER_TOKEN", "")},
    )
    print("WORKLOG_API_URL should be your Render API URL.")
    print("DISCORD_REDIRECT_URI should be https://YOUR-VERCEL-DOMAIN.vercel.app/api/auth/callback/discord")

    missing_root = [
        key
        for key in [
            "DATABASE_URL",
            "DISCORD_TOKEN",
            "DISCORD_GUILD_ID",
            "WORKLOG_CHANNEL_ID",
            "REVIEW_CHANNEL_ID",
            "DIGEST_TRIGGER_TOKEN",
        ]
        if not root_env.get(key)
    ]
    missing_web = [
        key
        for key in [
            "WEB_AUTH_SECRET",
            "DISCORD_CLIENT_ID",
            "DISCORD_CLIENT_SECRET",
        ]
        if not web_env.get(key)
    ]
    provider = root_env.get("EMBEDDING_PROVIDER", "openai").lower()
    if provider == "gemini" and not root_env.get("GEMINI_API_KEY"):
        missing_root.append("GEMINI_API_KEY")
    if provider == "openai" and not root_env.get("OPENAI_API_KEY"):
        missing_root.append("OPENAI_API_KEY")

    if missing_root or missing_web:
        print("\n## Missing locally\n")
        for key in missing_root + missing_web:
            print(f"- {key}")
        raise SystemExit(1)

    print("\nAll required local env keys are present.")


if __name__ == "__main__":
    main()
