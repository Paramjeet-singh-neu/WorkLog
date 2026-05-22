from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.embeddings import average_vectors, make_embedding_provider, split_skills
from shared.models import Match, Update, User


class SkillMatcher:
    def __init__(self) -> None:
        settings = get_settings()
        self.provider = make_embedding_provider(settings)

    async def embed(self, text: str) -> list[float]:
        return await self.provider.embed(text)

    async def embed_skills(self, skills_text: str) -> list[float]:
        phrases = split_skills(skills_text)
        if not phrases:
            return []
        return average_vectors(await self.provider.embed_many(phrases))

    async def find_and_record_matches(
        self,
        session: AsyncSession,
        update: Update,
        blocker_body: str,
    ) -> list[tuple[Match, User]]:
        blocker_embedding = await self.embed(blocker_body)
        cooldown_cutoff = datetime.now(UTC) - timedelta(hours=24)

        distance = User.skills_embedding.cosine_distance(blocker_embedding).label("distance")
        result = await session.execute(
            select(User, distance)
            .where(User.id != update.author_id)
            .where(User.skills_embedding.is_not(None))
            .where(or_(User.last_matched_at.is_(None), User.last_matched_at < cooldown_cutoff))
            .order_by(distance)
            .limit(5)
        )
        users = [row.User for row in result][:3]

        matches: list[tuple[Match, User]] = []
        now = datetime.now(UTC)
        for user in users:
            match = Match(update_id=update.id, matched_user_id=user.id)
            user.last_matched_at = now
            session.add(match)
            matches.append((match, user))

        await session.flush()
        return matches
