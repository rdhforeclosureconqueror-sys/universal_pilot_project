"""Sync DB schema with models safely

Revision ID: sync_schema_guard_001
Revises: c6489d4d49af  
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# IMPORTANT:
# Replace this with whatever `alembic heads` shows
revision = "sync_schema_guard_001"
down_revision = "6f4b2c1b2a8d"  # <-- CHANGE THIS
branch_labels = None
depends_on = None


def column_exists(inspector, table_name, column_name):
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(inspector, table_name):
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # -------------------------------------------------
    # LEADS TABLE SAFETY CHECKS
    # -------------------------------------------------
    if table_exists(inspector, "leads"):

        if not column_exists(inspector, "leads", "county"):
            op.add_column("leads", sa.Column("county", sa.String(), nullable=True))

        if not column_exists(inspector, "leads", "trustee"):
            op.add_column("leads", sa.Column("trustee", sa.String(), nullable=True))

        if not column_exists(inspector, "leads", "mortgagor"):
            op.add_column("leads", sa.Column("mortgagor", sa.String(), nullable=True))

        if not column_exists(inspector, "leads", "mortgagee"):
            op.add_column("leads", sa.Column("mortgagee", sa.String(), nullable=True))

        if not column_exists(inspector, "leads", "auction_date"):
            op.add_column(
                "leads",
                sa.Column("auction_date", sa.DateTime(timezone=True), nullable=True),
            )

        if not column_exists(inspector, "leads", "case_number"):
            op.add_column("leads", sa.Column("case_number", sa.String(), nullable=True))

        if not column_exists(inspector, "leads", "opening_bid"):
            op.add_column("leads", sa.Column("opening_bid", sa.Float(), nullable=True))

    # -------------------------------------------------
    # AUCTION IMPORTS TABLE SAFETY CHECKS
    # -------------------------------------------------
    if table_exists(inspector, "auction_imports"):
        if not column_exists(inspector, "auction_imports", "file_type"):
            op.add_column(
                "auction_imports",
                sa.Column("file_type", sa.String(), nullable=True),
            )


def downgrade():
    # Intentionally empty.
    # We do NOT want automatic drops in production.
    pass
