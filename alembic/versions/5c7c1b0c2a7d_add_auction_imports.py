"""add auction imports table

Revision ID: 5c7c1b0c2a7d
Revises: 3b6c6b7c4f12
Create Date: 2026-01-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "5c7c1b0c2a7d"
down_revision = "3b6c6b7c4f12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auction_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column("file_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="received"),
        sa.Column("records_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("auction_imports")
