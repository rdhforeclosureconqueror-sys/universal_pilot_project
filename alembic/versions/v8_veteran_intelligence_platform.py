"""Add veteran intelligence platform tables.

Revision ID: v8_veteran_intelligence_platform
Revises: v7_module_registry_foundation
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v8_veteran_intelligence_platform"
down_revision = "v7_module_registry_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "veteran_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_of_service", sa.String(), nullable=True),
        sa.Column("years_of_service", sa.Integer(), nullable=True),
        sa.Column("discharge_status", sa.String(), nullable=True),
        sa.Column("disability_rating", sa.Integer(), nullable=True),
        sa.Column("permanent_and_total_status", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("combat_service", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("dependent_status", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("state_of_residence", sa.String(), nullable=True),
        sa.Column("homeowner_status", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("mortgage_status", sa.String(), nullable=True),
        sa.Column("foreclosure_risk", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("income_level", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_veteran_profiles_case_id_cases"),
        sa.PrimaryKeyConstraint("id", name="pk_veteran_profiles"),
        sa.UniqueConstraint("case_id", name="uq_veteran_profiles_case_id"),
    )
    op.create_index("ix_veteran_profiles_case_id", "veteran_profiles", ["case_id"], unique=True)

    op.create_table(
        "benefit_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("benefit_name", sa.String(), nullable=False),
        sa.Column("eligibility_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required_documents", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("estimated_value", sa.Float(), nullable=True),
        sa.Column("application_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_benefit_registry"),
        sa.UniqueConstraint("benefit_name", name="uq_benefit_registry_benefit_name"),
    )

    op.create_table(
        "benefit_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benefit_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default=sa.text("'NOT_STARTED'"), nullable=False),
        sa.Column("status_notes", sa.String(), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_benefit_progress_case_id_cases"),
        sa.PrimaryKeyConstraint("id", name="pk_benefit_progress"),
        sa.UniqueConstraint("case_id", "benefit_name", name="uq_benefit_progress_case_benefit"),
    )
    op.create_index("ix_benefit_progress_case_id", "benefit_progress", ["case_id"], unique=False)

    op.create_table(
        "benefit_discovery_aggregates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("state_of_residence", sa.String(), nullable=False),
        sa.Column("benefit_name", sa.String(), nullable=False),
        sa.Column("discovery_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_benefit_discovery_aggregates"),
        sa.UniqueConstraint("state_of_residence", "benefit_name", name="uq_benefit_aggregate_state_benefit"),
    )


def downgrade() -> None:
    op.drop_table("benefit_discovery_aggregates")
    op.drop_index("ix_benefit_progress_case_id", table_name="benefit_progress")
    op.drop_table("benefit_progress")
    op.drop_table("benefit_registry")
    op.drop_index("ix_veteran_profiles_case_id", table_name="veteran_profiles")
    op.drop_table("veteran_profiles")
