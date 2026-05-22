from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models import Comment, Kudo, Update, User
from shared.schemas import CommentRead, UpdateSocial


async def get_user_by_discord_id(session: AsyncSession, discord_id: int) -> User | None:
    return (await session.scalars(select(User).where(User.discord_id == discord_id))).one_or_none()


async def get_update_or_none(session: AsyncSession, update_id: int) -> Update | None:
    return await session.get(Update, update_id)


async def add_comment(
    session: AsyncSession,
    update_id: int,
    author: User,
    body: str,
) -> Comment:
    comment = Comment(update_id=update_id, author_id=author.id, body=body.strip())
    session.add(comment)
    await session.flush()
    loaded = (
        await session.scalars(
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.id == comment.id)
        )
    ).one()
    return loaded


async def toggle_kudo(session: AsyncSession, update_id: int, user: User) -> bool:
    existing = (
        await session.scalars(
            select(Kudo).where(Kudo.update_id == update_id, Kudo.user_id == user.id)
        )
    ).one_or_none()
    if existing:
        await session.delete(existing)
        await session.flush()
        return False

    session.add(Kudo(update_id=update_id, user_id=user.id))
    await session.flush()
    return True


async def social_for_update(
    session: AsyncSession,
    update_id: int,
    viewer_user_id: int | None = None,
) -> UpdateSocial:
    comments = (
        await session.scalars(
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.update_id == update_id)
            .order_by(Comment.created_at)
        )
    ).all()

    kudo_count = await session.scalar(
        select(func.count()).select_from(Kudo).where(Kudo.update_id == update_id)
    )
    viewer_has_kudo = False
    if viewer_user_id is not None:
        viewer_has_kudo = (
            await session.scalars(
                select(Kudo.id).where(
                    Kudo.update_id == update_id,
                    Kudo.user_id == viewer_user_id,
                )
            )
        ).first() is not None

    return UpdateSocial(
        update_id=update_id,
        comments=[CommentRead.model_validate(comment) for comment in comments],
        kudo_count=int(kudo_count or 0),
        viewer_has_kudo=viewer_has_kudo,
    )


async def social_for_updates(
    session: AsyncSession,
    update_ids: list[int],
    viewer_discord_id: int | None = None,
) -> dict[int, UpdateSocial]:
    if not update_ids:
        return {}

    viewer_user_id: int | None = None
    if viewer_discord_id is not None:
        viewer = await get_user_by_discord_id(session, viewer_discord_id)
        viewer_user_id = viewer.id if viewer else None

    comments = (
        await session.scalars(
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.update_id.in_(update_ids))
            .order_by(Comment.created_at)
        )
    ).all()

    kudo_rows = (
        await session.execute(
            select(Kudo.update_id, func.count())
            .where(Kudo.update_id.in_(update_ids))
            .group_by(Kudo.update_id)
        )
    ).all()
    kudo_counts = {update_id: count for update_id, count in kudo_rows}

    viewer_kudo_update_ids: set[int] = set()
    if viewer_user_id is not None:
        viewer_kudo_update_ids = set(
            await session.scalars(
                select(Kudo.update_id).where(
                    Kudo.update_id.in_(update_ids),
                    Kudo.user_id == viewer_user_id,
                )
            )
        )

    comments_by_update: dict[int, list[CommentRead]] = {update_id: [] for update_id in update_ids}
    for comment in comments:
        comments_by_update[comment.update_id].append(CommentRead.model_validate(comment))

    return {
        update_id: UpdateSocial(
            update_id=update_id,
            comments=comments_by_update.get(update_id, []),
            kudo_count=int(kudo_counts.get(update_id, 0)),
            viewer_has_kudo=update_id in viewer_kudo_update_ids,
        )
        for update_id in update_ids
    }
