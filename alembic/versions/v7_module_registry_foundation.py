"""Add module registry foundation table.

Revision ID: v7_module_registry_foundation
Revises: v6_userrole_add_user
Create Date: 2026-03-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v7_module_registry_foundation"
down_revision = "v6_userrole_add_user"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "module_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("module_name", sa.String(), nullable=False),
        sa.Column("module_type", sa.String(), nullable=False),
        sa.Column("version", sa.String(), server_default=sa.text("'1.0.0'"), nullable=False),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required_services", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("data_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("allowed_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("validation_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("policy_validation_status", sa.String(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_module_registry"),
        sa.UniqueConstraint("module_name", "version", name="uq_module_registry_name_version"),
    )


def downgrade() -> None:
    op.drop_table("module_registry")
