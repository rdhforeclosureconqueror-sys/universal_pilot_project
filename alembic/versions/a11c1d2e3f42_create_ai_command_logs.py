"""Create ai_command_logs feature table.

Revision ID: a11c1d2e3f42
Revises: a11c1d2e3f41
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a11c1d2e3f42"
down_revision = "a11c1d2e3f41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_command_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("ai_response", sa.String(), nullable=False),
        sa.Column("actions_triggered", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_command_logs_user_id", "ai_command_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_command_logs_user_id", table_name="ai_command_logs")
    op.drop_table("ai_command_logs")
