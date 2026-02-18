"""governance guards + immutability enforcement

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
    # DOCUMENTS IMMUTABILITY
    # -------------------------------------------------

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_documents_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
            'documents are immutable; operation=% is not allowed',
            TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_prevent_documents_update
        BEFORE UPDATE ON documents
        FOR EACH ROW
        EXECUTE FUNCTION prevent_documents_mutation();
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_prevent_documents_delete
        BEFORE DELETE ON documents
        FOR EACH ROW
        EXECUTE FUNCTION prevent_documents_mutation();
        """
    )

    # -------------------------------------------------
    # AUDIT LOGS IMMUTABILITY
    # -------------------------------------------------

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_logs_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
            'audit_logs are immutable; operation=% is not allowed',
            TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_prevent_audit_logs_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_logs_mutation();
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_prevent_audit_logs_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_logs_mutation();
        """
    )


# -------------------------------------------------
# DOWNGRADE
# -------------------------------------------------

def downgrade() -> None:

    op.execute(
        "DROP TRIGGER IF EXISTS trg_prevent_audit_logs_delete ON audit_logs;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_prevent_audit_logs_update ON audit_logs;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_prevent_documents_delete ON documents;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_prevent_documents_update ON documents;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_enforce_workflow_override_limit ON workflow_overrides;"
    )

    op.execute(
        "DROP FUNCTION IF EXISTS prevent_audit_logs_mutation();"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS prevent_documents_mutation();"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS enforce_workflow_override_limit();"
    )
