from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.digest import build_digest_preview, post_digest_to_discord
from api.feed import latest_updates, mark_updates_seen, ranked_feed_for_viewer
from api.social import (
    add_comment,
    get_update_or_none,
    get_user_by_discord_id,
    social_for_update,
    social_for_updates,
    toggle_kudo,
)
from shared.config import Settings, get_settings
from shared.db import get_session
from shared.models import Comment, Kudo, Project, ProjectFollow, Update, UpdateKind, User
from shared.schemas import (
    AdminSummary,
    CommentRead,
    CreateCommentRequest,
    DigestResponse,
    MarkFeedSeenRequest,
    ProjectRead,
    ProjectSocial,
    ShowcaseProject,
    UpdateRead,
    UpdateSocial,
    UpdateWithRelations,
    UserProfile,
    UserRead,
)

app = FastAPI(title="Worklog API")

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
AuthorizationHeader = Annotated[str | None, Header()]


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "Worklog API",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health")
async def health(session: SessionDep) -> dict[str, str]:
    await session.execute(text("select 1"))
    return {"ok": "true"}


@app.post("/digest/trigger", response_model=DigestResponse)
async def trigger_digest(
    session: SessionDep,
    settings: SettingsDep,
    authorization: AuthorizationHeader = None,
) -> DigestResponse:
    if settings.digest_trigger_token:
        expected = f"Bearer {settings.digest_trigger_token}"
        if authorization != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    preview = await build_digest_preview(session)
    await post_digest_to_discord(settings, preview)
    return DigestResponse(ok=True, message=preview)


@app.get("/digest/preview", response_model=DigestResponse)
async def preview_digest(
    session: SessionDep,
    settings: SettingsDep,
    authorization: AuthorizationHeader = None,
) -> DigestResponse:
    if settings.digest_trigger_token:
        expected = f"Bearer {settings.digest_trigger_token}"
        if authorization != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    preview = await build_digest_preview(session)
    return DigestResponse(ok=True, message=preview)


@app.get("/updates", response_model=list[UpdateWithRelations])
async def updates(session: SessionDep, limit: int = 50) -> list[Update]:
    safe_limit = min(max(limit, 1), 100)
    return await latest_updates(session, safe_limit)


@app.get("/feed", response_model=list[UpdateWithRelations])
async def ranked_feed(
    session: SessionDep,
    viewer_discord_id: int,
    limit: int = 50,
) -> list[Update]:
    viewer = (
        await session.scalars(select(User).where(User.discord_id == viewer_discord_id))
    ).one_or_none()
    if viewer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viewer not found")

    safe_limit = min(max(limit, 1), 100)
    result = await ranked_feed_for_viewer(session, viewer, safe_limit)
    await session.commit()
    return result


@app.post("/feed/seen")
async def feed_seen(
    session: SessionDep,
    viewer_discord_id: int,
    payload: MarkFeedSeenRequest,
) -> dict[str, str]:
    viewer = (
        await session.scalars(select(User).where(User.discord_id == viewer_discord_id))
    ).one_or_none()
    if viewer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viewer not found")

    await mark_updates_seen(session, viewer.id, payload.update_ids)
    await session.commit()
    return {"ok": "true"}


@app.get("/updates/{update_id}", response_model=UpdateWithRelations)
async def update_detail(update_id: int, session: SessionDep) -> Update:
    update = (
        await session.scalars(
            select(Update)
            .options(selectinload(Update.author), selectinload(Update.project))
            .where(Update.id == update_id)
        )
    ).one_or_none()
    if update is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Update not found")
    return update


@app.get("/social", response_model=dict[int, UpdateSocial])
async def batch_social(
    session: SessionDep,
    update_ids: str,
    viewer_discord_id: int | None = None,
) -> dict[int, UpdateSocial]:
    ids = [int(value) for value in update_ids.split(",") if value.strip().isdigit()]
    if not ids:
        return {}
    safe_ids = ids[:100]
    return await social_for_updates(session, safe_ids, viewer_discord_id)


@app.get("/updates/{update_id}/social", response_model=UpdateSocial)
async def update_social(
    session: SessionDep,
    update_id: int,
    viewer_discord_id: int | None = None,
) -> UpdateSocial:
    update = await get_update_or_none(session, update_id)
    if update is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Update not found")

    viewer_user_id: int | None = None
    if viewer_discord_id is not None:
        viewer = await get_user_by_discord_id(session, viewer_discord_id)
        viewer_user_id = viewer.id if viewer else None

    return await social_for_update(session, update_id, viewer_user_id)


@app.post("/updates/{update_id}/comments", response_model=CommentRead)
async def create_comment(
    session: SessionDep,
    update_id: int,
    author_discord_id: int,
    payload: CreateCommentRequest,
) -> CommentRead:
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment body is required")
    if len(body) > 2000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment is too long")

    update = await get_update_or_none(session, update_id)
    if update is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Update not found")

    author = await get_user_by_discord_id(session, author_discord_id)
    if author is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

    comment = await add_comment(session, update_id, author, body)
    await session.commit()
    return CommentRead.model_validate(comment)


@app.post("/updates/{update_id}/kudos")
async def toggle_update_kudo(
    session: SessionDep,
    update_id: int,
    user_discord_id: int,
) -> dict[str, bool | int]:
    update = await get_update_or_none(session, update_id)
    if update is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Update not found")

    user = await get_user_by_discord_id(session, user_discord_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    added = await toggle_kudo(session, update_id, user)
    await session.commit()
    kudo_count = await session.scalar(
        select(func.count()).select_from(Kudo).where(Kudo.update_id == update_id)
    )
    return {"added": added, "kudo_count": int(kudo_count or 0)}


@app.get("/projects/{project_id}/social", response_model=ProjectSocial)
async def project_social(
    project_id: int,
    session: SessionDep,
    viewer_discord_id: int | None = None,
) -> ProjectSocial:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    follower_count = await session.scalar(
        select(func.count()).select_from(ProjectFollow).where(ProjectFollow.project_id == project_id)
    )
    viewer_following = False
    if viewer_discord_id is not None:
        viewer = await get_user_by_discord_id(session, viewer_discord_id)
        if viewer is not None:
            viewer_following = (
                await session.get(ProjectFollow, (viewer.id, project_id))
            ) is not None

    return ProjectSocial(
        project_id=project_id,
        follower_count=int(follower_count or 0),
        viewer_following=viewer_following,
    )


@app.post("/projects/{project_id}/follow")
async def toggle_project_follow(
    project_id: int,
    session: SessionDep,
    viewer_discord_id: int,
) -> dict[str, bool | int]:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    viewer = await get_user_by_discord_id(session, viewer_discord_id)
    if viewer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viewer not found")

    existing = await session.get(ProjectFollow, (viewer.id, project_id))
    following = existing is None
    if existing is None:
        session.add(ProjectFollow(follower_id=viewer.id, project_id=project_id))
    else:
        await session.delete(existing)

    await session.commit()
    follower_count = await session.scalar(
        select(func.count()).select_from(ProjectFollow).where(ProjectFollow.project_id == project_id)
    )
    return {"following": following, "follower_count": int(follower_count or 0)}


@app.get("/showcase", response_model=list[ShowcaseProject])
async def showcase(session: SessionDep, limit: int = 20) -> list[ShowcaseProject]:
    safe_limit = min(max(limit, 1), 50)
    rows = (
        await session.execute(
            select(
                Project,
                User,
                func.count(Update.id.distinct()).label("update_count"),
                func.count(Update.id.distinct())
                .filter(Update.kind == UpdateKind.shipped)
                .label("shipped_count"),
                func.count(ProjectFollow.follower_id.distinct()).label("follower_count"),
                func.max(Update.created_at).label("latest_update_at"),
            )
            .join(User, User.id == Project.owner_id)
            .outerjoin(Update, Update.project_id == Project.id)
            .outerjoin(ProjectFollow, ProjectFollow.project_id == Project.id)
            .group_by(Project.id, User.id)
            .order_by(desc(func.max(Update.created_at)).nullslast(), desc(func.count(Update.id.distinct())))
            .limit(safe_limit)
        )
    ).all()

    return [
        ShowcaseProject(
            project=ProjectRead.model_validate(project),
            owner=UserRead.model_validate(owner),
            update_count=int(update_count or 0),
            shipped_count=int(shipped_count or 0),
            follower_count=int(follower_count or 0),
            latest_update_at=latest_update_at,
        )
        for project, owner, update_count, shipped_count, follower_count, latest_update_at in rows
    ]


@app.get("/admin/summary", response_model=AdminSummary)
async def admin_summary(
    session: SessionDep,
    settings: SettingsDep,
    authorization: AuthorizationHeader = None,
) -> AdminSummary:
    if settings.digest_trigger_token:
        expected = f"Bearer {settings.digest_trigger_token}"
        if authorization != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    return AdminSummary(
        users=int(await session.scalar(select(func.count()).select_from(User)) or 0),
        projects=int(await session.scalar(select(func.count()).select_from(Project)) or 0),
        updates=int(await session.scalar(select(func.count()).select_from(Update)) or 0),
        comments=int(await session.scalar(select(func.count()).select_from(Comment)) or 0),
        kudos=int(await session.scalar(select(func.count()).select_from(Kudo)) or 0),
        blocked_updates=int(
            await session.scalar(
                select(func.count()).select_from(Update).where(Update.kind == UpdateKind.blocked)
            )
            or 0
        ),
        review_requests=int(
            await session.scalar(
                select(func.count()).select_from(Update).where(Update.kind == UpdateKind.seeking_review)
            )
            or 0
        ),
    )


@app.get("/users/discord/{discord_id}", response_model=UserRead)
async def user_by_discord_id(discord_id: int, session: SessionDep) -> User:
    user = (await session.scalars(select(User).where(User.discord_id == discord_id))).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@app.get("/users/{user_id}", response_model=UserProfile)
async def user_profile(user_id: int, session: SessionDep) -> UserProfile:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updates_result = await session.scalars(
        select(Update)
        .where(Update.author_id == user_id)
        .order_by(desc(Update.created_at))
        .limit(50)
    )
    projects_result = await session.scalars(
        select(Project).where(Project.owner_id == user_id).order_by(desc(Project.created_at))
    )

    return UserProfile(
        user=UserRead.model_validate(user),
        updates=[UpdateRead.model_validate(update) for update in updates_result],
        projects=[ProjectRead.model_validate(project) for project in projects_result],
    )


@app.get("/projects/{project_id}", response_model=ProjectRead)
async def project_detail(project_id: int, session: SessionDep) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@app.get("/projects/{project_id}/updates", response_model=list[UpdateWithRelations])
async def project_updates(project_id: int, session: SessionDep) -> list[Update]:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return (
        await session.scalars(
            select(Update)
            .options(selectinload(Update.author), selectinload(Update.project))
            .where(Update.project_id == project_id)
            .order_by(desc(Update.created_at))
            .limit(100)
        )
    ).all()
