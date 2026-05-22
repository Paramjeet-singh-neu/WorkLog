"""social feedback tables

Revision ID: 0003_social_feedback
Revises: 0002_feed_ranking
Create Date: 2026-05-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_social_feedback"
down_revision: str | None = "0002_feed_ranking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("update_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["update_id"], ["updates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_comments_author_id"), "comments", ["author_id"], unique=False)
    op.create_index(op.f("ix_comments_created_at"), "comments", ["created_at"], unique=False)
    op.create_index(op.f("ix_comments_update_id"), "comments", ["update_id"], unique=False)

    op.create_table(
        "kudos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("update_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["update_id"], ["updates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("update_id", "user_id", name="uq_kudos_pair"),
    )
    op.create_index(op.f("ix_kudos_update_id"), "kudos", ["update_id"], unique=False)
    op.create_index(op.f("ix_kudos_user_id"), "kudos", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_kudos_user_id"), table_name="kudos")
    op.drop_index(op.f("ix_kudos_update_id"), table_name="kudos")
    op.drop_table("kudos")
    op.drop_index(op.f("ix_comments_update_id"), table_name="comments")
    op.drop_index(op.f("ix_comments_created_at"), table_name="comments")
    op.drop_index(op.f("ix_comments_author_id"), table_name="comments")
    op.drop_table("comments")
