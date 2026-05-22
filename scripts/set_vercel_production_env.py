#!/usr/bin/env python3
"""Push production env vars to the linked Vercel project."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def add_env(key: str, value: str) -> None:
    if not value:
        print(f"skip {key}: missing")
        return
    subprocess.run(
        ["vercel", "env", "add", key, "production", "--force"],
        input=f"{value}\n".encode(),
        cwd=WEB,
        check=True,
    )
    print(f"set {key}")


def main() -> None:
    root_env = load_env(ROOT / ".env")
    web_env = load_env(WEB / ".env.local")

    api_url = sys.argv[1] if len(sys.argv) > 1 else "https://worklog-api.onrender.com"
    vercel_domain = sys.argv[2] if len(sys.argv) > 2 else None

    if vercel_domain is None:
        result = subprocess.run(
            ["vercel", "ls", "--json"],
            cwd=WEB,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise SystemExit(
                "Pass the Vercel domain as the second argument, e.g. "
                "`python scripts/set_vercel_production_env.py https://api.onrender.com "
                "your-app.vercel.app`"
            )
        deployments = json.loads(result.stdout).get("deployments", [])
        production = next(
            (
                deployment
                for deployment in deployments
                if deployment.get("target") == "production" and deployment.get("state") == "READY"
            ),
            None,
        )
        if production is None:
            raise SystemExit("No ready production Vercel deployment found.")
        vercel_domain = production["url"]

    redirect_uri = f"https://{vercel_domain.rstrip('/')}/api/auth/callback/discord"
    digest_token = web_env.get("DIGEST_TRIGGER_TOKEN") or root_env.get("DIGEST_TRIGGER_TOKEN", "")

    add_env("WORKLOG_API_URL", api_url.rstrip("/"))
    add_env("WEB_AUTH_SECRET", web_env.get("WEB_AUTH_SECRET", ""))
    add_env("DISCORD_CLIENT_ID", web_env.get("DISCORD_CLIENT_ID", ""))
    add_env("DISCORD_CLIENT_SECRET", web_env.get("DISCORD_CLIENT_SECRET", ""))
    add_env("DISCORD_REDIRECT_URI", redirect_uri)
    if digest_token:
        add_env("DIGEST_TRIGGER_TOKEN", digest_token)

    print(f"\nProduction redirect URI (add in Discord Developer Portal):\n{redirect_uri}\n")
    print("Redeploy with: cd web && vercel --prod")


if __name__ == "__main__":
    main()
