from datetime import UTC, datetime, timedelta

import aiohttp
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.config import Settings
from shared.models import Comment, Kudo, Update, UpdateKind


KIND_LABELS = {
    UpdateKind.shipped: "Shipped",
    UpdateKind.progress: "Progress",
    UpdateKind.blocked: "Blocked",
    UpdateKind.seeking_review: "Needs review",
}


async def build_digest_preview(session: AsyncSession, limit: int = 10, days: int = 7) -> str:
    since = datetime.now(UTC) - timedelta(days=days)
    updates = (
        await session.scalars(
            select(Update)
            .options(selectinload(Update.author), selectinload(Update.project))
            .where(Update.created_at >= since)
            .order_by(desc(Update.created_at))
            .limit(limit)
        )
    ).all()
    if not updates:
        return f"No Worklog updates in the last {days} days."

    counts = dict(
        (
            await session.execute(
                select(Update.kind, func.count())
                .where(Update.created_at >= since)
                .group_by(Update.kind)
            )
        ).all()
    )

    update_ids = [update.id for update in updates]
    comment_count = await session.scalar(
        select(func.count()).select_from(Comment).where(Comment.update_id.in_(update_ids))
    )
    kudo_count = await session.scalar(
        select(func.count()).select_from(Kudo).where(Kudo.update_id.in_(update_ids))
    )

    lines = [f"**Worklog weekly digest** — last {days} days"]
    lines.append(
        " · ".join(
            f"{KIND_LABELS[kind]}: {int(counts.get(kind, 0))}" for kind in UpdateKind
        )
    )
    lines.append(f"Comments: {int(comment_count or 0)} · Kudos: {int(kudo_count or 0)}")
    lines.append("")

    for update in updates:
        author = update.author.name if update.author else "Unknown"
        project = f" · {update.project.title}" if update.project else ""
        lines.append(
            f"- **{KIND_LABELS[update.kind]}** by {author}{project}: {update.body[:180]}"
        )
    return "\n".join(lines)


async def post_digest_to_discord(settings: Settings, content: str) -> None:
    if not settings.discord_token:
        raise RuntimeError("DISCORD_TOKEN is required to post a digest")

    channel_id = settings.digest_channel_id or settings.worklog_channel_id
    if not channel_id:
        raise RuntimeError("DIGEST_CHANNEL_ID or WORKLOG_CHANNEL_ID is required")

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {settings.discord_token}",
        "Content-Type": "application/json",
    }
    # Discord messages are capped at 2000 characters.
    payload = {"content": content[:2000]}
    async with aiohttp.ClientSession() as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status >= 400:
            body = await response.text()
            raise RuntimeError(f"Discord digest post failed: {response.status} {body}")
