"""align leads and auction imports fields

Revision ID: 6f4b2c1b2a8d
Revises: 5c7c1b0c2a7d
Create Date: 2026-02-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "6f4b2c1b2a8d"
down_revision = "5c7c1b0c2a7d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("auction_imports", sa.Column("file_type", sa.String(), nullable=True))
    op.add_column("leads", sa.Column("county", sa.String(), nullable=True))
    op.add_column("leads", sa.Column("trustee", sa.String(), nullable=True))
    op.add_column("leads", sa.Column("mortgagor", sa.String(), nullable=True))
    op.add_column("leads", sa.Column("mortgagee", sa.String(), nullable=True))
    op.add_column("leads", sa.Column("auction_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leads", sa.Column("case_number", sa.String(), nullable=True))
    op.add_column("leads", sa.Column("opening_bid", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "opening_bid")
    op.drop_column("leads", "case_number")
    op.drop_column("leads", "auction_date")
    op.drop_column("leads", "mortgagee")
    op.drop_column("leads", "mortgagor")
    op.drop_column("leads", "trustee")
    op.drop_column("leads", "county")
    op.drop_column("auction_imports", "file_type")
