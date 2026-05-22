"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-20
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("discord_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("skills_text", sa.Text(), nullable=True),
        sa.Column("skills_embedding", pgvector.sqlalchemy.Vector(dim=1536), nullable=True),
        sa.Column("last_matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_discord_id"), "users", ["discord_id"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"], unique=False)

    op.create_table(
        "follows",
        sa.Column("follower_id", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("follower_id", "target_user_id"),
        sa.UniqueConstraint("follower_id", "target_user_id", name="uq_follows_pair"),
    )

    op.create_table(
        "updates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("discord_message_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("discord_message_id"),
    )
    op.create_index(op.f("ix_updates_author_id"), "updates", ["author_id"], unique=False)
    op.create_index(op.f("ix_updates_created_at"), "updates", ["created_at"], unique=False)
    op.create_index(op.f("ix_updates_kind"), "updates", ["kind"], unique=False)
    op.create_index(op.f("ix_updates_project_id"), "updates", ["project_id"], unique=False)

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("update_id", sa.Integer(), nullable=False),
        sa.Column("matched_user_id", sa.Integer(), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["matched_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["update_id"], ["updates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("update_id", "matched_user_id", name="uq_matches_pair"),
    )
    op.create_index(
        op.f("ix_matches_matched_user_id"),
        "matches",
        ["matched_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_matches_update_id"), "matches", ["update_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_matches_update_id"), table_name="matches")
    op.drop_index(op.f("ix_matches_matched_user_id"), table_name="matches")
    op.drop_table("matches")
    op.drop_index(op.f("ix_updates_project_id"), table_name="updates")
    op.drop_index(op.f("ix_updates_kind"), table_name="updates")
    op.drop_index(op.f("ix_updates_created_at"), table_name="updates")
    op.drop_index(op.f("ix_updates_author_id"), table_name="updates")
    op.drop_table("updates")
    op.drop_table("follows")
    op.drop_index(op.f("ix_projects_owner_id"), table_name="projects")
    op.drop_table("projects")
    op.drop_index(op.f("ix_users_discord_id"), table_name="users")
    op.drop_table("users")
