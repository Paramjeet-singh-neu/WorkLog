import logging

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Comment, Update, User

logger = logging.getLogger(__name__)


async def find_update_for_message(session: AsyncSession, message_id: int) -> Update | None:
    return (
        await session.scalars(select(Update).where(Update.discord_message_id == message_id))
    ).one_or_none()


async def notify_update_author(
    bot: discord.Client,
    author_discord_id: int,
    actor: discord.abc.User,
    message: str,
) -> None:
    if author_discord_id == actor.id:
        return
    try:
        recipient = await bot.fetch_user(author_discord_id)
        await recipient.send(message)
    except discord.DiscordException:
        logger.exception("Failed to notify update author %s", author_discord_id)


async def create_comment_from_discord(
    session: AsyncSession,
    update: Update,
    author: User,
    body: str,
) -> Comment:
    comment = Comment(update_id=update.id, author_id=author.id, body=body.strip())
    session.add(comment)
    await session.flush()
    return comment
