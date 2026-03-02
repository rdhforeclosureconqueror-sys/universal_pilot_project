"""Stripe settlement fields for membership installments.

Revision ID: v5_stripe_settlement_engine
Revises: v4_system_verification_framework
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa


revision = "v5_stripe_settlement_engine"
down_revision = "v4_system_verification_framework"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def _constraint_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {c["name"] for c in inspector.get_unique_constraints(table_name)}


def upgrade() -> None:
    existing_columns = _column_names("membership_installments")

    if "stripe_invoice_id" not in existing_columns:
        op.add_column("membership_installments", sa.Column("stripe_invoice_id", sa.Text(), nullable=True))

    if "amount_paid_cents" not in existing_columns:
        op.add_column("membership_installments", sa.Column("amount_paid_cents", sa.Integer(), nullable=True))

    if "paid_at" not in existing_columns:
        op.add_column("membership_installments", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))

    existing_constraints = _constraint_names("membership_installments")
    if "uq_membership_installments_stripe_invoice_id" not in existing_constraints:
        op.create_unique_constraint(
            "uq_membership_installments_stripe_invoice_id",
            "membership_installments",
            ["stripe_invoice_id"],
        )


def downgrade() -> None:
    existing_constraints = _constraint_names("membership_installments")
    if "uq_membership_installments_stripe_invoice_id" in existing_constraints:
        op.drop_constraint(
            "uq_membership_installments_stripe_invoice_id",
            "membership_installments",
            type_="unique",
        )

    existing_columns = _column_names("membership_installments")
    if "amount_paid_cents" in existing_columns:
        op.drop_column("membership_installments", "amount_paid_cents")
    if "stripe_invoice_id" in existing_columns:
        op.drop_column("membership_installments", "stripe_invoice_id")
    # `paid_at` may pre-exist from prior revisions; preserve historical field on downgrade.
