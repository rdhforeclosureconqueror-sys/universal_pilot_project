"""add deal scores table

Revision ID: 6a1b2d9c4e5f
Revises: 5c7c1b0c2a7d
Create Date: 2026-01-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "6a1b2d9c4e5f"
down_revision = "5c7c1b0c2a7d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deal_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("exit_strategy", sa.String(), nullable=False),
        sa.Column("urgency_days", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
    )


def downgrade() -> None:
    op.drop_table("deal_scores")
