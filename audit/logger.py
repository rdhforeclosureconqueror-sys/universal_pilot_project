from models.audit_logs import AuditLog
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
from typing import Optional, Union

def log_audit(
    db: Session,
    *,
    case_id: str,
    actor_id: Optional[str],
    actor_is_ai: bool = False,
    action_type: str,
    reason_code: str,
    before_state: dict,
    after_state: dict,
    policy_version_id: Optional[str] = None
):
    audit = AuditLog(
        id=str(uuid4()),
        case_id=case_id,
        actor_id=actor_id,
        actor_is_ai=actor_is_ai,
        action_type=action_type,
        reason_code=reason_code,
        before_state=before_state,
        after_state=after_state,
        policy_version_id=policy_version_id,
        created_at=datetime.utcnow()
    )
    db.add(audit)
