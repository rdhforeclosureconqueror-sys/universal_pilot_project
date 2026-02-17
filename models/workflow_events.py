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


@event.listens_for(Document, "after_insert")
def _document_after_insert(mapper, connection, target):
    _sync_case_on_event(connection, target.case_id)


@event.listens_for(AuditLog, "after_insert")
def _audit_after_insert(mapper, connection, target):
    _sync_case_on_event(connection, target.case_id)
