#!/usr/bin/env python3
"""Force-sync Worklog slash commands to your Discord test guild."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import discord  # noqa: E402

from bot.main import bot  # noqa: E402 — registers slash commands on bot.tree
from shared.config import get_settings  # noqa: E402


def _print_synced(synced: list[discord.app_commands.AppCommand]) -> None:
    print(f"Synced {len(synced)} top-level command(s):")
    for cmd in synced:
        if cmd.options:
            subcommands = ", ".join(option.name for option in cmd.options)
            print(f"  /{cmd.name} -> {subcommands}")
        else:
            print(f"  /{cmd.name}")


async def main() -> None:
    settings = get_settings()
    if not settings.discord_token:
        raise SystemExit("DISCORD_TOKEN is missing in .env")
    if not settings.discord_guild_id:
        raise SystemExit("DISCORD_GUILD_ID is missing in .env")

    guild = discord.Object(id=settings.discord_guild_id)

    @bot.event
    async def on_ready() -> None:
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        _print_synced(synced)
        follow = next((cmd for cmd in synced if cmd.name == "follow"), None)
        if follow is None:
            print("\nWARNING: /follow was not synced.")
        elif not any(option.name == "project" for option in (follow.options or [])):
            print("\nWARNING: /follow project subcommand is missing after sync.")
        else:
            print("\nOK: /follow project is registered. Restart Discord if it still does not appear.")
        await bot.close()

    try:
        await bot.start(settings.discord_token)
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
