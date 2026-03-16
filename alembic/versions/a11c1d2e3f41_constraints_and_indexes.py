"""Constraints and index normalization split from oversized autogenerate.

Revision ID: a11c1d2e3f41
Revises: a11c1d2e3f40
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a11c1d2e3f41"
down_revision = "a11c1d2e3f40"
branch_labels = None
depends_on = None


def _index_exists(bind, index_name: str) -> bool:
    return bool(
        bind.execute(
            sa.text("SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = :name"),
            {"name": index_name},
        ).scalar()
    )


def _constraint_exists(bind, table_name: str, constraint_name: str) -> bool:
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                  AND constraint_name = :constraint_name
                """
            ),
            {"table_name": table_name, "constraint_name": constraint_name},
        ).scalar()
    )


def upgrade() -> None:
    bind = op.get_bind()

    # Index parity (additive only, no destructive index drops).
    if not _index_exists(bind, "ix_cases_canonical_key"):
        op.create_index("ix_cases_canonical_key", "cases", ["canonical_key"], unique=True)

    # Constraint parity (additive only).
    if not _constraint_exists(bind, "cases", "uq_cases_property_auction_date"):
        op.create_unique_constraint(
            "uq_cases_property_auction_date",
            "cases",
            ["property_id", "auction_date"],
        )

    if not _constraint_exists(bind, "cases", "cases_property_id_fkey"):
        op.create_foreign_key(
            "cases_property_id_fkey",
            "cases",
            "properties",
            ["property_id"],
            ["id"],
        )

    # Server default normalization for drift-prone member-layer columns.
    op.execute("ALTER TABLE applications ALTER COLUMN created_at SET DEFAULT now()")
    op.execute("ALTER TABLE memberships ALTER COLUMN created_at SET DEFAULT now()")
    op.execute("ALTER TABLE membership_installments ALTER COLUMN created_at SET DEFAULT now()")


def downgrade() -> None:
    bind = op.get_bind()

    op.execute("ALTER TABLE membership_installments ALTER COLUMN created_at DROP DEFAULT")
    op.execute("ALTER TABLE memberships ALTER COLUMN created_at DROP DEFAULT")
    op.execute("ALTER TABLE applications ALTER COLUMN created_at DROP DEFAULT")

    if _constraint_exists(bind, "cases", "cases_property_id_fkey"):
        op.drop_constraint("cases_property_id_fkey", "cases", type_="foreignkey")

    if _constraint_exists(bind, "cases", "uq_cases_property_auction_date"):
        op.drop_constraint("uq_cases_property_auction_date", "cases", type_="unique")

    if _index_exists(bind, "ix_cases_canonical_key"):
        op.drop_index("ix_cases_canonical_key", table_name="cases")
