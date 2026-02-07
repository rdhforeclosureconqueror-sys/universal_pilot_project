"""add file_type to auction_imports

Revision ID: c6489d4d49af
Revises: b2e1f0a9c002
Create Date: 2026-02-07
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c6489d4d49af"
down_revision = "b2e1f0a9c002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auction_imports",
        sa.Column("file_type", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("auction_imports", "file_type")
