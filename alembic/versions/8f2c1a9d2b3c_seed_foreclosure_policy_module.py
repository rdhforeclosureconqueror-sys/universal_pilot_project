"""Seed foreclosure policy module

Revision ID: 8f2c1a9d2b3c
Revises: 662249195df8
Create Date: 2026-01-22 06:12:00.000000

"""
from datetime import datetime
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

from policy.foreclosure_policy_module import FORECLOSURE_POLICY_MODULE

# revision identifiers, used by Alembic.
revision = "8f2c1a9d2b3c"
down_revision = "662249195df8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    policy_versions = sa.table(
        "policy_versions",
        sa.column("id", sa.String()),
        sa.column("program_key", sa.String()),
        sa.column("version_tag", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("config_json", sa.JSON()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    existing = connection.execute(
        sa.select(policy_versions.c.id).where(
            policy_versions.c.program_key == FORECLOSURE_POLICY_MODULE["program_key"],
            policy_versions.c.version_tag == FORECLOSURE_POLICY_MODULE["version_tag"],
        )
    ).first()

    if existing:
        return

    connection.execute(
        policy_versions.insert().values(
            id=str(uuid4()),
            program_key=FORECLOSURE_POLICY_MODULE["program_key"],
            version_tag=FORECLOSURE_POLICY_MODULE["version_tag"],
            is_active=True,
            config_json=FORECLOSURE_POLICY_MODULE["config"],
            created_at=datetime.utcnow(),
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    policy_versions = sa.table(
        "policy_versions",
        sa.column("program_key", sa.String()),
        sa.column("version_tag", sa.String()),
    )
    connection.execute(
        policy_versions.delete().where(
            policy_versions.c.program_key == FORECLOSURE_POLICY_MODULE["program_key"],
            policy_versions.c.version_tag == FORECLOSURE_POLICY_MODULE["version_tag"],
        )
    )
