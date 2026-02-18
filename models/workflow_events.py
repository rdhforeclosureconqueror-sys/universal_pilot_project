from sqlalchemy import event
from sqlalchemy.orm import Session

from models.audit_logs import AuditLog
from models.documents import Document
from services.workflow_engine import sync_case_workflow


def _sync_case_on_event(connection, case_id):
    if not case_id:
        return
    session = Session(bind=connection)
    try:
        sync_case_workflow(session, case_id)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


# Evidence tables are immutable after insert to preserve audit integrity.
@event.listens_for(Document, "before_update")
def _document_before_update(mapper, connection, target):
    raise ValueError("Documents are immutable; create a new document record instead of update")


@event.listens_for(Document, "before_delete")
def _document_before_delete(mapper, connection, target):
    raise ValueError("Documents are immutable; deletion is not allowed")


@event.listens_for(AuditLog, "before_update")
def _audit_before_update(mapper, connection, target):
    raise ValueError("Audit logs are immutable; update is not allowed")


@event.listens_for(AuditLog, "before_delete")
def _audit_before_delete(mapper, connection, target):
    raise ValueError("Audit logs are immutable; deletion is not allowed")


@event.listens_for(Document, "after_insert")
def _document_after_insert(mapper, connection, target):
    _sync_case_on_event(connection, target.case_id)


@event.listens_for(AuditLog, "after_insert")
def _audit_after_insert(mapper, connection, target):
    _sync_case_on_event(connection, target.case_id)
