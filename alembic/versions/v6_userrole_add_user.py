"""Add 'user' value to userrole enum for default registration role.

Revision ID: v6_userrole_add_user
Revises: v5_stripe_settlement_engine
Create Date: 2026-03-03
"""

from alembic import op


revision = "v6_userrole_add_user"
down_revision = "v5_stripe_settlement_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'user'")


def downgrade() -> None:
    # PostgreSQL enum value removal is non-trivial; keep no-op downgrade.
    pass
