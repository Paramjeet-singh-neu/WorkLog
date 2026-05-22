from datetime import date, datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, BigInteger, Date, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UpdateKind(StrEnum):
    shipped = "shipped"
    progress = "progress"
    blocked = "blocked"
    seeking_review = "seeking_review"


class ProjectStatus(StrEnum):
    active = "active"
    shipped = "shipped"
    paused = "paused"
    abandoned = "abandoned"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    skills_text: Mapped[str | None] = mapped_column(Text)
    skills_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
    updates: Mapped[list["Update"]] = relationship(back_populates="author")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False),
        default=ProjectStatus.active,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    owner: Mapped[User] = relationship(back_populates="projects")
    updates: Mapped[list["Update"]] = relationship(back_populates="project")


class Update(Base):
    __tablename__ = "updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True,
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[UpdateKind] = mapped_column(Enum(UpdateKind, native_enum=False), index=True)
    body: Mapped[str] = mapped_column(Text)
    discord_message_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    author: Mapped[User] = relationship(back_populates="updates")
    project: Mapped[Project | None] = relationship(back_populates="updates")
    matches: Mapped[list["Match"]] = relationship(back_populates="update")
    comments: Mapped[list["Comment"]] = relationship(back_populates="update")
    kudos: Mapped[list["Kudo"]] = relationship(back_populates="update")


class ProjectFollow(Base):
    __tablename__ = "project_follows"
    __table_args__ = (UniqueConstraint("follower_id", "project_id", name="uq_project_follows_pair"),)

    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "target_user_id", name="uq_follows_pair"),)

    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    target_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("update_id", "matched_user_id", name="uq_matches_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    update_id: Mapped[int] = mapped_column(ForeignKey("updates.id", ondelete="CASCADE"), index=True)
    matched_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    update: Mapped[Update] = relationship(back_populates="matches")


class FeedSeen(Base):
    __tablename__ = "feed_seen"
    __table_args__ = (UniqueConstraint("viewer_user_id", "update_id", name="uq_feed_seen_pair"),)

    viewer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    update_id: Mapped[int] = mapped_column(
        ForeignKey("updates.id", ondelete="CASCADE"),
        primary_key=True,
    )
    seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    update_id: Mapped[int] = mapped_column(
        ForeignKey("updates.id", ondelete="CASCADE"),
        index=True,
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    update: Mapped[Update] = relationship(back_populates="comments")
    author: Mapped[User] = relationship()


class Kudo(Base):
    __tablename__ = "kudos"
    __table_args__ = (UniqueConstraint("update_id", "user_id", name="uq_kudos_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    update_id: Mapped[int] = mapped_column(
        ForeignKey("updates.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    update: Mapped[Update] = relationship(back_populates="kudos")
    user: Mapped[User] = relationship()


class FeedCache(Base):
    __tablename__ = "feed_cache"

    viewer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    update_ids: Mapped[list[int]] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class DigestRun(Base):
    __tablename__ = "digest_runs"

    digest_date: Mapped[date] = mapped_column(Date, primary_key=True)
    discord_message_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
