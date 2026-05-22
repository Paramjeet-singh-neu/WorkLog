"""digest run tracking

Revision ID: 0004_digest_runs
Revises: 0003_social_feedback
Create Date: 2026-05-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_digest_runs"
down_revision: str | None = "0003_social_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "digest_runs",
        sa.Column("digest_date", sa.Date(), nullable=False),
        sa.Column("discord_message_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("digest_date"),
        sa.UniqueConstraint("discord_message_id"),
    )


def downgrade() -> None:
    op.drop_table("digest_runs")
