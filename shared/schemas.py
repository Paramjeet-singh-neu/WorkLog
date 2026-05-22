from datetime import datetime

from pydantic import BaseModel, ConfigDict

from shared.models import ProjectStatus, UpdateKind


class UserRead(BaseModel):
    id: int
    discord_id: int
    name: str
    skills_text: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UpdateRead(BaseModel):
    id: int
    project_id: int | None
    author_id: int
    kind: UpdateKind
    body: str
    discord_message_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectRead(BaseModel):
    id: int
    owner_id: int
    title: str
    description: str | None
    status: ProjectStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectSocial(BaseModel):
    project_id: int
    follower_count: int
    viewer_following: bool


class ShowcaseProject(BaseModel):
    project: ProjectRead
    owner: UserRead
    update_count: int
    shipped_count: int
    follower_count: int
    latest_update_at: datetime | None


class AdminSummary(BaseModel):
    users: int
    projects: int
    updates: int
    comments: int
    kudos: int
    blocked_updates: int
    review_requests: int


class UpdateWithRelations(BaseModel):
    id: int
    project_id: int | None
    author_id: int
    kind: UpdateKind
    body: str
    discord_message_id: int | None
    created_at: datetime
    author: UserRead
    project: ProjectRead | None

    model_config = ConfigDict(from_attributes=True)


class UserProfile(BaseModel):
    user: UserRead
    updates: list[UpdateRead]
    projects: list[ProjectRead]


class MarkFeedSeenRequest(BaseModel):
    update_ids: list[int]


class CommentRead(BaseModel):
    id: int
    update_id: int
    author_id: int
    body: str
    created_at: datetime
    author: UserRead

    model_config = ConfigDict(from_attributes=True)


class UpdateSocial(BaseModel):
    update_id: int
    comments: list[CommentRead]
    kudo_count: int
    viewer_has_kudo: bool


class CreateCommentRequest(BaseModel):
    body: str


class DigestResponse(BaseModel):
    ok: bool
    message: str
