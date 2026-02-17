"""merge current heads

Revision ID: a1c9d9e0f001
Revises: 6a1b2d9c4e5f, 6f4b2c1b2a8d
Create Date: 2026-02-07 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1c9d9e0f001"
down_revision = ("6a1b2d9c4e5f", "6f4b2c1b2a8d")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
