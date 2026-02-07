from uuid import uuid4

from audit.logger import log_audit
from models.audit_logs import AuditLog


def test_log_audit_writes_expected_fields(db_session):
    case_id = uuid4()
    log_audit(
        db=db_session,
        case_id=case_id,
        actor_id=uuid4(),
        action_type="case_created",
        reason_code="intake_received",
        before_state={},
        after_state={"status": "intake_submitted"},
        policy_version_id=None,
    )
    db_session.commit()

    logs = db_session.query(AuditLog).filter(AuditLog.case_id == case_id).all()
    assert len(logs) == 1
    assert logs[0].before_state == {}
    assert logs[0].after_state["status"] == "intake_submitted"
