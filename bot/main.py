import logging
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks
from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert

from api.digest import build_digest_preview
from bot.matcher import SkillMatcher
from bot.social import create_comment_from_discord, find_update_for_message, notify_update_author
from shared.config import get_settings
from shared.db import SessionLocal
from shared.models import DigestRun, Follow, Kudo, Match, Project, ProjectFollow, Update, UpdateKind, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


class HelpButton(discord.ui.View):
    def __init__(
        self,
        bot: commands.Bot,
        match_id: int,
        worklog_channel_id: int,
        message_id: int,
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.match_id = match_id
        self.worklog_channel_id = worklog_channel_id
        self.message_id = message_id

    @discord.ui.button(label="I can help", style=discord.ButtonStyle.primary)
    async def can_help(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        channel = self.bot.get_channel(self.worklog_channel_id)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("I could not find the worklog channel.")
            return

        try:
            message = await channel.fetch_message(self.message_id)
            thread = message.thread or await message.create_thread(name="Blocker help")
        except discord.DiscordException:
            await interaction.response.send_message("I could not open the blocker thread.")
            return

        async with SessionLocal() as session:
            match = await session.get(Match, self.match_id)
            if match and match.responded_at is None:
                match.responded_at = datetime.now(UTC)
                await session.commit()

        try:
            if interaction.user:
                await thread.add_user(interaction.user)
            await thread.send(f"{interaction.user.mention} can help with this blocker.")
        except discord.DiscordException:
            logger.exception("Failed to add helper to blocker thread")

        await interaction.response.send_message("Thanks. I opened the thread for you.")


class WorklogBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.matcher: SkillMatcher | None = None

    async def setup_hook(self) -> None:
        self.matcher = SkillMatcher()
        weekly_digest.start()
        if settings.discord_guild_id:
            guild = discord.Object(id=settings.discord_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


bot = WorklogBot()


@tasks.loop(hours=1)
async def weekly_digest() -> None:
    now = datetime.now(UTC)
    if now.weekday() != 0 or now.hour != settings.digest_post_hour_utc:
        return

    channel_id = settings.digest_channel_id or settings.worklog_channel_id
    if not channel_id:
        return

    async with SessionLocal() as session:
        digest_date = now.date()
        existing = await session.get(DigestRun, digest_date)
        if existing is not None:
            return

        content = await build_digest_preview(session)

    channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
    if not isinstance(channel, discord.abc.Messageable):
        logger.error("Digest channel %s is not messageable", channel_id)
        return

    message = await channel.send(content)
    async with SessionLocal() as session:
        session.add(DigestRun(digest_date=now.date(), discord_message_id=message.id))
        await session.commit()


@weekly_digest.before_loop
async def before_weekly_digest() -> None:
    await bot.wait_until_ready()


async def upsert_user(discord_user: discord.abc.User, skills_text: str | None = None) -> User:
    async with SessionLocal() as session:
        values = {
            "discord_id": discord_user.id,
            "name": discord_user.display_name,
        }
        if skills_text is not None:
            if bot.matcher is None:
                raise RuntimeError("Skill matcher is not initialized")
            values["skills_text"] = skills_text
            values["skills_embedding"] = await bot.matcher.embed_skills(skills_text)

        stmt = (
            insert(User)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[User.discord_id],
                set_=values,
            )
            .returning(User)
        )
        user = (await session.scalars(stmt)).one()
        await session.commit()
        return user


async def get_or_create_user(session, discord_user: discord.abc.User) -> User:
    user = (
        await session.scalars(select(User).where(User.discord_id == discord_user.id))
    ).one_or_none()
    if user:
        if user.name != discord_user.display_name:
            user.name = discord_user.display_name
        return user

    user = User(discord_id=discord_user.id, name=discord_user.display_name)
    session.add(user)
    await session.flush()
    return user


def make_update_embed(author: discord.abc.User, kind: UpdateKind, body: str) -> discord.Embed:
    colors = {
        UpdateKind.shipped: discord.Color.green(),
        UpdateKind.progress: discord.Color.blue(),
        UpdateKind.blocked: discord.Color.orange(),
        UpdateKind.seeking_review: discord.Color.purple(),
    }
    title = {
        UpdateKind.shipped: "Shipped",
        UpdateKind.progress: "Progress",
        UpdateKind.blocked: "Blocked",
        UpdateKind.seeking_review: "Review requested",
    }[kind]
    embed = discord.Embed(title=title, description=body, color=colors[kind])
    embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
    embed.timestamp = datetime.now(UTC)
    return embed


async def publish_update(
    interaction: discord.Interaction,
    kind: UpdateKind,
    body: str,
    channel_id: int,
) -> None:
    channel = bot.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "The target Worklog channel is not configured.",
            ephemeral=True,
        )
        return
    await interaction.response.defer(ephemeral=True)

    async with SessionLocal() as session:
        author = await get_or_create_user(session, interaction.user)
        update = Update(author_id=author.id, kind=kind, body=body)
        session.add(update)
        await session.flush()

        embed = make_update_embed(interaction.user, kind, body)
        message = await channel.send(embed=embed)
        update.discord_message_id = message.id

        matched: list[tuple[Match, User]] = []
        if kind == UpdateKind.blocked:
            if bot.matcher is None:
                raise RuntimeError("Skill matcher is not initialized")
            matched = await bot.matcher.find_and_record_matches(session, update, body)

        follower_ids = (
            await session.scalars(
                select(User.discord_id)
                .join(Follow, Follow.follower_id == User.id)
                .where(Follow.target_user_id == author.id)
            )
        ).all()
        await session.commit()

    await interaction.followup.send("Posted to Worklog.", ephemeral=True)

    if kind == UpdateKind.blocked and settings.worklog_channel_id:
        for match, user in matched:
            member = interaction.guild.get_member(user.discord_id) if interaction.guild else None
            recipient = member or await bot.fetch_user(user.discord_id)
            view = HelpButton(bot, match.id, settings.worklog_channel_id, message.id)
            try:
                await recipient.send(
                    f"{interaction.user.display_name} is blocked and may match your skills:\n\n"
                    f"> {body}\n\nClick below to jump into a thread.",
                    view=view,
                )
            except discord.DiscordException:
                logger.exception("Failed to DM matched user %s", user.discord_id)

    for follower_id in follower_ids:
        try:
            follower = await bot.fetch_user(follower_id)
            await follower.send(
                f"{interaction.user.display_name} posted a Worklog update in {channel.mention}:\n"
                f"{message.jump_url}"
            )
        except discord.DiscordException:
            logger.exception("Failed to DM follower %s", follower_id)


@bot.tree.command(name="skills", description="Tell Worklog what you can help with.")
@app_commands.describe(skills="Comma-separated skills, tools, or topics.")
async def skills(interaction: discord.Interaction, skills: str) -> None:
    await interaction.response.defer(ephemeral=True)
    await upsert_user(interaction.user, skills)
    await interaction.followup.send("Saved your skills for blocker routing.", ephemeral=True)


post_group = app_commands.Group(name="post", description="Post a structured Worklog update.")


@post_group.command(name="shipped", description="Post shipped work.")
async def post_shipped(interaction: discord.Interaction, message: str) -> None:
    if not settings.worklog_channel_id:
        await interaction.response.send_message(
            "WORKLOG_CHANNEL_ID is not configured.",
            ephemeral=True,
        )
        return
    await publish_update(interaction, UpdateKind.shipped, message, settings.worklog_channel_id)


@post_group.command(name="progress", description="Post progress.")
async def post_progress(interaction: discord.Interaction, message: str) -> None:
    if not settings.worklog_channel_id:
        await interaction.response.send_message(
            "WORKLOG_CHANNEL_ID is not configured.",
            ephemeral=True,
        )
        return
    await publish_update(interaction, UpdateKind.progress, message, settings.worklog_channel_id)


@post_group.command(name="blocked", description="Post a blocker and route it to matched helpers.")
async def post_blocked(interaction: discord.Interaction, message: str) -> None:
    if not settings.worklog_channel_id:
        await interaction.response.send_message(
            "WORKLOG_CHANNEL_ID is not configured.",
            ephemeral=True,
        )
        return
    await publish_update(interaction, UpdateKind.blocked, message, settings.worklog_channel_id)


@post_group.command(name="review", description="Request review on a link.")
@app_commands.describe(link="PR, demo, repo, or artifact link.")
async def post_review(interaction: discord.Interaction, link: str) -> None:
    channel_id = settings.review_channel_id or settings.worklog_channel_id
    if not channel_id:
        await interaction.response.send_message(
            "No review or worklog channel is configured.",
            ephemeral=True,
        )
        return
    await publish_update(interaction, UpdateKind.seeking_review, link, channel_id)


bot.tree.add_command(post_group)


follow_group = app_commands.Group(name="follow", description="Follow people or projects.")


@follow_group.command(name="user", description="DM me when this person posts.")
async def follow_user(interaction: discord.Interaction, user: discord.Member) -> None:
    if user.id == interaction.user.id:
        await interaction.response.send_message("You already see your own updates.", ephemeral=True)
        return

    async with SessionLocal() as session:
        follower = await get_or_create_user(session, interaction.user)
        target = await get_or_create_user(session, user)
        stmt = (
            insert(Follow)
            .values(follower_id=follower.id, target_user_id=target.id)
            .on_conflict_do_nothing()
        )
        await session.execute(stmt)
        await session.commit()

    await interaction.response.send_message(
        f"You are now following {user.display_name}.",
        ephemeral=True,
    )


@follow_group.command(name="project", description="Follow a project for ranked feed boosts.")
@app_commands.describe(project_id="Project ID shown on the web project page.")
async def follow_project(interaction: discord.Interaction, project_id: int) -> None:
    async with SessionLocal() as session:
        project = await session.get(Project, project_id)
        if project is None:
            await interaction.response.send_message("That project was not found.", ephemeral=True)
            return

        follower = await get_or_create_user(session, interaction.user)
        existing = await session.get(ProjectFollow, (follower.id, project_id))
        if existing is None:
            session.add(ProjectFollow(follower_id=follower.id, project_id=project_id))
            action = "following"
        else:
            await session.delete(existing)
            action = "no longer following"
        await session.commit()

    await interaction.response.send_message(
        f"You are {action} project #{project_id}: {project.title}.",
        ephemeral=True,
    )


bot.tree.add_command(follow_group)


@bot.tree.command(name="kudos", description="Give or remove kudos on a Worklog update.")
@app_commands.describe(update_id="Worklog update ID (shown on the web feed).")
async def kudos(interaction: discord.Interaction, update_id: int) -> None:
    async with SessionLocal() as session:
        update = await session.get(Update, update_id)
        if update is None:
            await interaction.response.send_message("That update was not found.", ephemeral=True)
            return

        user = await get_or_create_user(session, interaction.user)
        existing = (
            await session.scalars(
                select(Kudo).where(Kudo.update_id == update_id, Kudo.user_id == user.id)
            )
        ).one_or_none()

        if existing:
            await session.delete(existing)
            await session.commit()
            action = "removed your kudos from"
        else:
            session.add(Kudo(update_id=update_id, user_id=user.id))
            await session.commit()
            action = "gave kudos to"
            author = await session.get(User, update.author_id)
            if author:
                await notify_update_author(
                    bot,
                    author.discord_id,
                    interaction.user,
                    f"{interaction.user.display_name} gave kudos to your update:\n> {update.body[:200]}",
                )

        count = await session.scalar(
            select(func.count()).select_from(Kudo).where(Kudo.update_id == update_id)
        )

    await interaction.response.send_message(
        f"You {action} update #{update_id}. Total kudos: {int(count or 0)}.",
        ephemeral=True,
    )


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot or not message.reference or not message.reference.message_id:
        return

    channel_ids = {settings.worklog_channel_id, settings.review_channel_id}
    channel_ids.discard(None)
    if message.channel.id not in channel_ids:
        return

    body = message.content.strip()
    if not body:
        return
    if len(body) > 2000:
        body = body[:2000]

    async with SessionLocal() as session:
        update = await find_update_for_message(session, message.reference.message_id)
        if update is None:
            return

        author = await get_or_create_user(session, message.author)
        await create_comment_from_discord(session, update, author, body)
        update_author = await session.get(User, update.author_id)
        await session.commit()

    if update_author:
        await notify_update_author(
            bot,
            update_author.discord_id,
            message.author,
            f"{message.author.display_name} commented on your update:\n> {body[:500]}",
        )


@bot.tree.command(name="me", description="DM me my recent Worklog activity.")
async def me(interaction: discord.Interaction) -> None:
    async with SessionLocal() as session:
        user = (
            await session.scalars(select(User).where(User.discord_id == interaction.user.id))
        ).one_or_none()
        if not user:
            await interaction.response.send_message("No Worklog activity yet.", ephemeral=True)
            return
        updates = (
            await session.scalars(
                select(Update)
                .where(Update.author_id == user.id)
                .order_by(desc(Update.created_at))
                .limit(5)
            )
        ).all()

    if not updates:
        summary = "No updates yet. Try `/post progress` when you have something to share."
    else:
        summary = "\n".join(f"- {update.kind.value}: {update.body[:160]}" for update in updates)

    try:
        await interaction.user.send(f"Your recent Worklog activity:\n{summary}")
        await interaction.response.send_message(
            "I sent your activity summary by DM.",
            ephemeral=True,
        )
    except discord.DiscordException:
        await interaction.response.send_message(
            "I could not DM you. Check your privacy settings.",
            ephemeral=True,
        )


def main() -> None:
    if not settings.discord_token:
        raise RuntimeError("DISCORD_TOKEN is required")
    bot.run(settings.discord_token)


if __name__ == "__main__":
    main()
