from __future__ import annotations

import argparse
import asyncio
import importlib.util
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REQUIRED_ENV = [
    "DATABASE_URL",
    "DISCORD_TOKEN",
    "DISCORD_GUILD_ID",
    "WORKLOG_CHANNEL_ID",
    "REVIEW_CHANNEL_ID",
    "DIGEST_TRIGGER_TOKEN",
]

OPTIONAL_ENV = [
    "EMBEDDING_PROVIDER",
    "EMBEDDING_DIMENSIONS",
    "OPENAI_EMBEDDING_MODEL",
    "GEMINI_EMBEDDING_MODEL",
    "PUBLIC_BASE_URL",
]

DEPENDENCIES = [
    ("discord", "discord.py"),
    ("fastapi", "fastapi"),
    ("google.genai", "google-genai"),
    ("openai", "openai"),
    ("pgvector", "pgvector"),
    ("sqlalchemy", "sqlalchemy"),
    ("asyncpg", "asyncpg"),
    ("alembic", "alembic"),
    ("uvicorn", "uvicorn"),
]


def load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def status(ok: bool, label: str, detail: str = "") -> bool:
    marker = "PASS" if ok else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{marker}] {label}{suffix}")
    return ok


def info(label: str, detail: str = "") -> None:
    suffix = f" - {detail}" if detail else ""
    print(f"[INFO] {label}{suffix}")


def check_python() -> bool:
    version = sys.version_info
    return status(
        version >= (3, 11),
        "Python version",
        f"{version.major}.{version.minor}.{version.micro}",
    )


def check_env() -> bool:
    ok = True
    for key in REQUIRED_ENV:
        value = os.getenv(key)
        ok = status(bool(value), f"Required env {key}") and ok

    provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower().strip()
    if provider == "openai":
        ok = status(bool(os.getenv("OPENAI_API_KEY")), "Required env OPENAI_API_KEY") and ok
    elif provider == "gemini":
        ok = status(bool(os.getenv("GEMINI_API_KEY")), "Required env GEMINI_API_KEY") and ok
    else:
        ok = status(False, "EMBEDDING_PROVIDER", "must be openai or gemini") and ok

    for key in OPTIONAL_ENV:
        value = os.getenv(key)
        info(f"Optional env {key}", value or "not set")

    return ok


def check_dependencies() -> bool:
    ok = True
    for module_name, package_name in DEPENDENCIES:
        found = importlib.util.find_spec(module_name) is not None
        ok = status(found, f"Dependency {package_name}") and ok
    return ok


async def check_database() -> bool:
    if not os.getenv("DATABASE_URL"):
        return status(False, "Database connectivity", "DATABASE_URL is missing")

    try:
        import sqlalchemy as sa
        from sqlalchemy.ext.asyncio import create_async_engine

        from shared.config import get_settings
    except ImportError as exc:
        return status(False, "Database connectivity", f"missing dependency: {exc.name}")

    settings = get_settings()
    engine = create_async_engine(
        settings.async_database_url,
        connect_args=settings.async_database_connect_args,
        pool_pre_ping=True,
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(sa.text("select 1"))
            vector_result = await connection.execute(
                sa.text("select exists(select 1 from pg_extension where extname = 'vector')")
            )
            has_vector = bool(vector_result.scalar())
    except Exception as exc:  # noqa: BLE001
        return status(False, "Database connectivity", str(exc))
    finally:
        await engine.dispose()

    db_ok = status(True, "Database connectivity")
    vector_ok = status(has_vector, "pgvector extension", "run `alembic upgrade head` if missing")
    return db_ok and vector_ok


def check_api_health() -> bool:
    base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    url = f"{base_url}/health"
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            body = response.read().decode("utf-8")
            return status(response.status == 200, "API health", body)
    except urllib.error.URLError as exc:
        return status(False, "API health", f"{url} unreachable: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local Worklog Phase 1 setup.")
    parser.add_argument(
        "--no-network",
        action="store_true",
        help="Skip database and API health checks.",
    )
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Skip the API health check but still check the database.",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    load_dotenv()

    print("Worklog Phase 1 doctor\n")

    ok = True
    ok = check_python() and ok
    ok = check_env() and ok
    ok = check_dependencies() and ok

    if not args.no_network:
        ok = await check_database() and ok
        if not args.skip_api:
            ok = check_api_health() and ok

    print()
    if ok:
        print("All checked items passed.")
        return 0

    print("Some checks failed. Fix the failures above, then run this script again.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
