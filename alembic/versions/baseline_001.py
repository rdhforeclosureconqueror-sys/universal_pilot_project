"""
Baseline migration - core system only

Revision ID: baseline_001
Revises: None
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "baseline_001"
down_revision = None
branch_labels = None
depends_on = None


# --------------------------------------------------
# CORE ENUMS (NON-WORKFLOW ONLY)
# --------------------------------------------------

case_status_enum = postgresql.ENUM(
    "intake_submitted",
    "intake_incomplete",
    "under_review",
    "in_progress",
    "program_completed_positive_outcome",
    "case_closed_other_outcome",
    "auction_intake",
    name="casestatus",
    create_type=False,
)

user_role_enum = postgresql.ENUM(
    "case_worker",
    "referral_coordinator",
    "admin",
    "audit_steward",
    "ai_policy_chair",
    "partner_org",
    name="userrole",
    create_type=False,
)


# --------------------------------------------------
# UPGRADE
# --------------------------------------------------

def upgrade():

    bind = op.get_bind()

    # Create core enums
    case_status_enum.create(bind, checkfirst=True)
    user_role_enum.create(bind, checkfirst=True)

    # --------------------------------------------------
    # USERS
    # --------------------------------------------------

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", user_role_enum, nullable=True),
        sa.Column("full_name", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
    )

    # --------------------------------------------------
    # PROPERTIES
    # --------------------------------------------------

    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(), nullable=False, unique=True),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("zip", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
    )

    # --------------------------------------------------
    # CASES
    # --------------------------------------------------

    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  primary_key=True, nullable=False),
        sa.Column("status", case_status_enum, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("properties.id")),
        sa.Column("program_key", sa.String()),
        sa.Column("case_type", sa.String()),
        sa.Column("meta", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
    )

    # --------------------------------------------------
    # LEADS
    # --------------------------------------------------

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  primary_key=True, nullable=False),
        sa.Column("lead_id", sa.String(), nullable=False, unique=True),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String()),
        sa.Column("state", sa.String()),
        sa.Column("zip", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
    )

    # --------------------------------------------------
    # AUCTION IMPORTS
    # --------------------------------------------------

    op.create_table(
        "auction_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  primary_key=True, nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String()),
        sa.Column("file_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("records_created", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String()),
        sa.Column("uploaded_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
    )


# --------------------------------------------------
# DOWNGRADE
# --------------------------------------------------

def downgrade():

    op.drop_table("auction_imports")
    op.drop_table("leads")
    op.drop_table("cases")
    op.drop_table("properties")
    op.drop_table("users")

    case_status_enum.drop(op.get_bind(), checkfirst=True)
    user_role_enum.drop(op.get_bind(), checkfirst=True)
