"""Add Phase 11 essential worker and lead intelligence tables.

Revision ID: v10_phase11_essential_worker_and_lead_intelligence
Revises: v9_foreclosure_housing_operating_system
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v10_phase11_essential_worker_and_lead_intelligence"
down_revision = "v9_foreclosure_housing_operating_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "essential_worker_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("profession", sa.String(), nullable=False),
        sa.Column("employer_type", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("annual_income", sa.Float(), nullable=True),
        sa.Column("first_time_homebuyer", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_essential_worker_profiles_case_id_cases"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_essential_worker_profiles_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_essential_worker_profiles"),
    )

    op.create_table(
        "essential_worker_benefit_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program", sa.String(), nullable=False),
        sa.Column("estimated_value", sa.Float(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["essential_worker_profiles.id"], name="fk_essential_worker_matches_profile"),
        sa.PrimaryKeyConstraint("id", name="pk_essential_worker_benefit_matches"),
    )

    op.create_table(
        "lead_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_lead_sources"),
        sa.UniqueConstraint("source_name", name="uq_lead_sources_source_name"),
    )

    op.create_table(
        "property_leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("property_address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("zip_code", sa.String(), nullable=True),
        sa.Column("foreclosure_stage", sa.String(), nullable=True),
        sa.Column("tax_delinquent", sa.String(), nullable=True),
        sa.Column("equity_estimate", sa.Float(), nullable=True),
        sa.Column("auction_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_occupancy", sa.String(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["lead_sources.id"], name="fk_property_leads_source_id_lead_sources"),
        sa.PrimaryKeyConstraint("id", name="pk_property_leads"),
        sa.UniqueConstraint("source_id", "property_address", name="uq_property_leads_source_address"),
    )

    op.create_table(
        "lead_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("grade", sa.String(), nullable=False),
        sa.Column("recommended_action", sa.String(), nullable=True),
        sa.Column("created_case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["property_leads.id"], name="fk_lead_scores_lead_id_property_leads"),
        sa.ForeignKeyConstraint(["created_case_id"], ["cases.id"], name="fk_lead_scores_created_case_id_cases"),
        sa.PrimaryKeyConstraint("id", name="pk_lead_scores"),
    )


def downgrade() -> None:
    op.drop_table("lead_scores")
    op.drop_table("property_leads")
    op.drop_table("lead_sources")
    op.drop_table("essential_worker_benefit_matches")
    op.drop_table("essential_worker_profiles")
