"""
Governance guards – workflow only

Revision ID: 002_governance_guards
Revises: 001_workflow_system
Create Date: 2026-02-18
"""

from alembic import op

# revision identifiers
revision = "002_governance_guards"
down_revision = "001_workflow_system"
branch_labels = None
depends_on = None


# -------------------------------------------------
# UPGRADE
# -------------------------------------------------

def upgrade() -> None:

    # -------------------------------------------------
    # LIMIT WORKFLOW OVERRIDES PER CASE (MAX 3)
    # -------------------------------------------------

    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_workflow_override_limit()
        RETURNS trigger AS $$
        DECLARE
            override_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO override_count
            FROM workflow_overrides
            WHERE case_id = NEW.case_id;

            IF override_count >= 3 THEN
                RAISE EXCEPTION
                'workflow override limit exceeded for case_id=%',
                NEW.case_id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_enforce_workflow_override_limit
        BEFORE INSERT ON workflow_overrides
        FOR EACH ROW
        EXECUTE FUNCTION enforce_workflow_override_limit();
        """
    )


# -------------------------------------------------
# DOWNGRADE
# -------------------------------------------------

def downgrade() -> None:

    op.execute(
        "DROP TRIGGER IF EXISTS trg_enforce_workflow_override_limit ON workflow_overrides;"
    )

    op.execute(
        "DROP FUNCTION IF EXISTS enforce_workflow_override_limit();"
    )
