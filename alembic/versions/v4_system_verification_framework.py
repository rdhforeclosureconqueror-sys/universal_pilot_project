"""System verification framework tables.

Revision ID: v4_system_verification_framework
Revises: v3_member_layer
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v4_system_verification_framework"
down_revision = "v3_member_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_phases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("environment", sa.String(length=20), nullable=False),
        sa.Column("phase_key", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_system_phases"),
        sa.UniqueConstraint("environment", "phase_key", name="uq_system_phases_environment_phase_key"),
    )

    op.create_table(
        "phase_verification_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("environment", sa.String(length=20), nullable=False),
        sa.Column("phase_key", sa.String(length=100), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_phase_verification_runs"),
    )

    op.create_index(
        "ix_system_phases_environment_phase_key",
        "system_phases",
        ["environment", "phase_key"],
        unique=False,
    )
    op.create_index(
        "ix_phase_verification_runs_environment_phase_key",
        "phase_verification_runs",
        ["environment", "phase_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_phase_verification_runs_environment_phase_key", table_name="phase_verification_runs")
    op.drop_index("ix_system_phases_environment_phase_key", table_name="system_phases")
    op.drop_table("phase_verification_runs")
    op.drop_table("system_phases")
