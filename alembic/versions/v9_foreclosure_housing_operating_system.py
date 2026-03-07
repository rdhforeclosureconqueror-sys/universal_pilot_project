"""Add Phase 9 foreclosure intelligence and housing operating system tables.

Revision ID: v9_foreclosure_housing_operating_system
Revises: v8_veteran_intelligence_platform
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v9_foreclosure_housing_operating_system"
down_revision = "v8_veteran_intelligence_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "foreclosure_case_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("zip_code", sa.String(), nullable=True),
        sa.Column("loan_balance", sa.Float(), nullable=True),
        sa.Column("estimated_property_value", sa.Float(), nullable=True),
        sa.Column("monthly_payment", sa.Float(), nullable=True),
        sa.Column("arrears_amount", sa.Float(), nullable=True),
        sa.Column("foreclosure_stage", sa.String(), nullable=True),
        sa.Column("auction_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lender_name", sa.String(), nullable=True),
        sa.Column("servicer_name", sa.String(), nullable=True),
        sa.Column("occupancy_status", sa.String(), nullable=True),
        sa.Column("homeowner_income", sa.Float(), nullable=True),
        sa.Column("homeowner_hardship_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_foreclosure_case_data_case_id_cases"),
        sa.PrimaryKeyConstraint("id", name="pk_foreclosure_case_data"),
        sa.UniqueConstraint("case_id", name="uq_foreclosure_case_data_case_id"),
    )

    op.create_table(
        "partner_organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("service_type", sa.String(), nullable=False),
        sa.Column("service_region", sa.String(), nullable=True),
        sa.Column("contact_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("api_endpoint", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_partner_organizations"),
    )

    op.create_table(
        "partner_referrals",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("routing_category", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_partner_referrals_case_id_cases"),
        sa.ForeignKeyConstraint(["partner_organization_id"], ["partner_organizations.id"], name="fk_partner_referrals_org_id_partner_orgs"),
        sa.PrimaryKeyConstraint("id", name="pk_partner_referrals"),
    )

    op.create_table(
        "property_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("property_address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("zip_code", sa.String(), nullable=True),
        sa.Column("acquisition_cost", sa.Float(), nullable=True),
        sa.Column("estimated_value", sa.Float(), nullable=True),
        sa.Column("loan_amount", sa.Float(), nullable=True),
        sa.Column("tenant_homeowner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lease_terms", sa.String(), nullable=True),
        sa.Column("equity_share_percentage", sa.Float(), nullable=True),
        sa.Column("portfolio_status", sa.String(), server_default=sa.text("'active'"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_property_assets_case_id_cases"),
        sa.PrimaryKeyConstraint("id", name="pk_property_assets"),
    )

    op.create_table(
        "membership_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("membership_status", sa.String(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("membership_type", sa.String(), server_default=sa.text("'cooperative'"), nullable=False),
        sa.Column("equity_share", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("voting_power", sa.Float(), server_default=sa.text("1"), nullable=False),
        sa.Column("join_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name="fk_membership_profiles_case_id_cases"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_membership_profiles_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_membership_profiles"),
    )

    op.create_table(
        "foreclosure_lead_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("import_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("property_address", sa.String(), nullable=False),
        sa.Column("foreclosure_stage", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_foreclosure_lead_imports"),
    )

    op.create_table(
        "training_guide_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("step_id", sa.String(), nullable=False),
        sa.Column("step_title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("related_endpoint", sa.String(), nullable=False),
        sa.Column("role_required", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_training_guide_steps"),
        sa.UniqueConstraint("step_id", name="uq_training_guide_steps_step_id"),
    )


def downgrade() -> None:
    op.drop_table("training_guide_steps")
    op.drop_table("foreclosure_lead_imports")
    op.drop_table("membership_profiles")
    op.drop_table("property_assets")
    op.drop_table("partner_referrals")
    op.drop_table("partner_organizations")
    op.drop_table("foreclosure_case_data")
