"""Add versioned household planner and private health aggregates."""

import sqlalchemy as sa
from alembic import op

revision = "hp20261014"
down_revision = "3527efeeec34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "household_planner_documents",
        sa.Column("id", sa.String(200), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
    )

    op.create_index("ix_household_planner_documents_created_at", "household_planner_documents", ["created_at"])


def downgrade() -> None:
    op.drop_table("household_planner_documents")
