"""Schema normalization split from oversized autogenerate.

Revision ID: a11c1d2e3f40
Revises: v10_phase11_essential_worker_and_lead_intelligence
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a11c1d2e3f40"
down_revision = "v10_phase11_essential_worker_and_lead_intelligence"
branch_labels = None
depends_on = None


def _column_type(bind, table_name: str, column_name: str) -> str | None:
    return bind.execute(
        sa.text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).scalar()


def _enum_exists(bind, enum_name: str) -> bool:
    return bool(
        bind.execute(
            sa.text("SELECT 1 FROM pg_type WHERE typname = :enum_name"),
            {"enum_name": enum_name},
        ).scalar()
    )


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Enum normalization: create missing credittype before any column usage.
    if not _enum_exists(bind, "credittype"):
        op.execute(
            """
            CREATE TYPE credittype AS ENUM (
                'testimonial_video',
                'referral',
                'volunteer',
                'training_module',
                'other'
            )
            """
        )

    # 2) Normalize credits.credit_type enum type if still bound to legacy credit_type.
    if _enum_exists(bind, "credit_type") and _enum_exists(bind, "credittype"):
        op.execute(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                JOIN pg_type t ON t.oid = a.atttypid
                WHERE c.relname = 'credits'
                  AND a.attname = 'credit_type'
                  AND t.typname = 'credit_type'
              ) THEN
                ALTER TABLE credits
                ALTER COLUMN credit_type
                TYPE credittype
                USING credit_type::text::credittype;
              END IF;
            END $$;
            """
        )

    # 3) JSONB -> JSON normalization (safe, conditional, only known model columns).
    for table_name, column_name in [
        ("cases", "meta"),
        ("documents", "meta"),
        ("outbox_queue", "payload"),
    ]:
        if _column_type(bind, table_name, column_name) == "jsonb":
            op.execute(
                sa.text(
                    f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE JSON USING {column_name}::json"
                )
            )

    # 4) Timestamp normalization example: properties.auction_date to timestamp without tz
    # to align with model definition when drift exists.
    if _column_type(bind, "properties", "auction_date") == "timestamp with time zone":
        op.execute(
            """
            ALTER TABLE properties
            ALTER COLUMN auction_date
            TYPE TIMESTAMP WITHOUT TIME ZONE
            USING auction_date AT TIME ZONE 'UTC'
            """
        )


def downgrade() -> None:
    bind = op.get_bind()

    # Revert timestamp normalization when needed.
    if _column_type(bind, "properties", "auction_date") == "timestamp without time zone":
        op.execute(
            """
            ALTER TABLE properties
            ALTER COLUMN auction_date
            TYPE TIMESTAMP WITH TIME ZONE
            USING auction_date AT TIME ZONE 'UTC'
            """
        )

    # Revert JSON normalization to JSONB when needed.
    for table_name, column_name in [
        ("cases", "meta"),
        ("documents", "meta"),
        ("outbox_queue", "payload"),
    ]:
        if _column_type(bind, table_name, column_name) == "json":
            op.execute(
                sa.text(
                    f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE JSONB USING {column_name}::jsonb"
                )
            )

    # Optionally map back to legacy enum if both enums are present.
    if _enum_exists(bind, "credit_type") and _enum_exists(bind, "credittype"):
        op.execute(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                JOIN pg_type t ON t.oid = a.atttypid
                WHERE c.relname = 'credits'
                  AND a.attname = 'credit_type'
                  AND t.typname = 'credittype'
              ) THEN
                ALTER TABLE credits
                ALTER COLUMN credit_type
                TYPE credit_type
                USING credit_type::text::credit_type;
              END IF;
            END $$;
            """
        )

    if _enum_exists(bind, "credittype"):
        op.execute("DROP TYPE IF EXISTS credittype")
