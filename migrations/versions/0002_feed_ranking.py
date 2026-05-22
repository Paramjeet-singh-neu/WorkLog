"""feed ranking tables

Revision ID: 0002_feed_ranking
Revises: 0001_initial_schema
Create Date: 2026-05-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_feed_ranking"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_follows",
        sa.Column("follower_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("follower_id", "project_id"),
        sa.UniqueConstraint("follower_id", "project_id", name="uq_project_follows_pair"),
    )

    op.create_table(
        "feed_seen",
        sa.Column("viewer_user_id", sa.Integer(), nullable=False),
        sa.Column("update_id", sa.Integer(), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["update_id"], ["updates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["viewer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("viewer_user_id", "update_id"),
        sa.UniqueConstraint("viewer_user_id", "update_id", name="uq_feed_seen_pair"),
    )

    op.create_table(
        "feed_cache",
        sa.Column("viewer_user_id", sa.Integer(), nullable=False),
        sa.Column("update_ids", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["viewer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("viewer_user_id"),
    )
    op.create_index(op.f("ix_feed_cache_expires_at"), "feed_cache", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_feed_cache_expires_at"), table_name="feed_cache")
    op.drop_table("feed_cache")
    op.drop_table("feed_seen")
    op.drop_table("project_follows")
