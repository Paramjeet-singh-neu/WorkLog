from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.config import get_settings
from shared.embeddings import make_embedding_provider
from shared.models import FeedCache, FeedSeen, Follow, ProjectFollow, Update, UpdateKind, User

KIND_SCORES = {
    UpdateKind.blocked: 50,
    UpdateKind.seeking_review: 40,
    UpdateKind.shipped: 20,
    UpdateKind.progress: 10,
}

FOLLOW_AUTHOR_BONUS = 30
FOLLOW_PROJECT_BONUS = 25
SKILL_MATCH_BONUS = 35
SEEN_DECAY = 0.3
TIME_DECAY_BASE = 0.95
CACHE_TTL = timedelta(minutes=5)
SKILL_MATCH_DISTANCE_THRESHOLD = 0.45


@dataclass
class ScoredUpdate:
    update: Update
    score: float


async def latest_updates(session: AsyncSession, limit: int = 50) -> list[Update]:
    return (
        await session.scalars(
            select(Update)
            .options(selectinload(Update.author), selectinload(Update.project))
            .order_by(desc(Update.created_at))
            .limit(limit)
        )
    ).all()


async def _followed_user_ids(session: AsyncSession, viewer_id: int) -> set[int]:
    rows = await session.scalars(select(Follow.target_user_id).where(Follow.follower_id == viewer_id))
    return set(rows)


async def _followed_project_ids(session: AsyncSession, viewer_id: int) -> set[int]:
    rows = await session.scalars(
        select(ProjectFollow.project_id).where(ProjectFollow.follower_id == viewer_id)
    )
    return set(rows)


async def _seen_update_ids(session: AsyncSession, viewer_id: int) -> set[int]:
    rows = await session.scalars(select(FeedSeen.update_id).where(FeedSeen.viewer_user_id == viewer_id))
    return set(rows)


def _time_decay(created_at: datetime, now: datetime) -> float:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    hours = max((now - created_at).total_seconds() / 3600, 0)
    return TIME_DECAY_BASE**hours


def _cosine_distance(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 1.0
    return 1 - (dot / (norm_a * norm_b))


async def _blocker_skill_distances(
    viewer: User,
    blocked_updates: list[Update],
) -> dict[int, float]:
    if viewer.skills_embedding is None or not blocked_updates:
        return {}

    settings = get_settings()
    provider = make_embedding_provider(settings)
    bodies = [update.body for update in blocked_updates]
    body_embeddings = await provider.embed_many(bodies)
    viewer_embedding = list(viewer.skills_embedding)

    return {
        update.id: _cosine_distance(viewer_embedding, embedding)
        for update, embedding in zip(blocked_updates, body_embeddings, strict=True)
    }


async def score_updates(
    session: AsyncSession,
    viewer: User,
    updates: list[Update],
) -> list[ScoredUpdate]:
    now = datetime.now(UTC)
    followed_users = await _followed_user_ids(session, viewer.id)
    followed_projects = await _followed_project_ids(session, viewer.id)
    seen_updates = await _seen_update_ids(session, viewer.id)

    blocked_updates = [update for update in updates if update.kind == UpdateKind.blocked]
    skill_distances = await _blocker_skill_distances(viewer, blocked_updates)

    scored: list[ScoredUpdate] = []
    for update in updates:
        score = float(KIND_SCORES.get(update.kind, 0))

        if update.author_id in followed_users:
            score += FOLLOW_AUTHOR_BONUS
        if update.project_id and update.project_id in followed_projects:
            score += FOLLOW_PROJECT_BONUS

        distance = skill_distances.get(update.id)
        if distance is not None and distance <= SKILL_MATCH_DISTANCE_THRESHOLD:
            score += SKILL_MATCH_BONUS

        score *= _time_decay(update.created_at, now)

        if update.id in seen_updates:
            score *= SEEN_DECAY

        scored.append(ScoredUpdate(update=update, score=score))

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored


async def _load_cached_feed(session: AsyncSession, viewer_id: int) -> list[Update] | None:
    now = datetime.now(UTC)
    cache = await session.get(FeedCache, viewer_id)
    if cache is None or cache.expires_at <= now:
        return None

    if not cache.update_ids:
        return []

    updates = (
        await session.scalars(
            select(Update)
            .options(selectinload(Update.author), selectinload(Update.project))
            .where(Update.id.in_(cache.update_ids))
        )
    ).all()
    by_id = {update.id: update for update in updates}
    return [by_id[update_id] for update_id in cache.update_ids if update_id in by_id]


async def _store_feed_cache(session: AsyncSession, viewer_id: int, update_ids: list[int]) -> None:
    now = datetime.now(UTC)
    cache = await session.get(FeedCache, viewer_id)
    if cache is None:
        cache = FeedCache(viewer_user_id=viewer_id, update_ids=update_ids)
        session.add(cache)
    else:
        cache.update_ids = update_ids
        cache.generated_at = now
    cache.expires_at = now + CACHE_TTL
    await session.flush()


async def ranked_feed_for_viewer(
    session: AsyncSession,
    viewer: User,
    limit: int = 50,
    use_cache: bool = True,
) -> list[Update]:
    if use_cache:
        cached = await _load_cached_feed(session, viewer.id)
        if cached is not None:
            return cached[:limit]

    candidates = (
        await session.scalars(
            select(Update)
            .options(selectinload(Update.author), selectinload(Update.project))
            .order_by(desc(Update.created_at))
            .limit(max(limit * 3, 100))
        )
    ).all()

    scored = await score_updates(session, viewer, candidates)
    ordered = [item.update for item in scored[:limit]]
    await _store_feed_cache(session, viewer.id, [update.id for update in ordered])
    return ordered


async def mark_updates_seen(
    session: AsyncSession,
    viewer_id: int,
    update_ids: list[int],
) -> None:
    if not update_ids:
        return

    now = datetime.now(UTC)
    for update_id in update_ids:
        seen = await session.get(FeedSeen, (viewer_id, update_id))
        if seen is None:
            session.add(FeedSeen(viewer_user_id=viewer_id, update_id=update_id, seen_at=now))
    await session.flush()


async def clear_expired_feed_cache(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    await session.execute(delete(FeedCache).where(FeedCache.expires_at <= now))
