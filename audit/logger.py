from datetime import datetime
from typing import Optional, Any
from uuid import uuid4

from sqlalchemy.orm import Session

from models.audit_logs import AuditLog


def log_audit(
    db: Session,
    *,
    case_id: Any,
    actor_id: Optional[Any],
    actor_is_ai: bool = False,
    action_type: str,
    reason_code: str,
    before_json: Optional[dict] = None,
    after_json: Optional[dict] = None,
    # backward-compatible aliases
    before_state: Optional[dict] = None,
    after_state: Optional[dict] = None,
    policy_version_id: Optional[Any] = None,
):
    if before_json is None:
        before_json = before_state or {}
    if after_json is None:
        after_json = after_state or {}

    audit = AuditLog(
        id=uuid4(),
        case_id=case_id,
        actor_id=actor_id,
        actor_is_ai=actor_is_ai,
        action_type=action_type,
        reason_code=reason_code,
        before_json=before_json,
        after_json=after_json,
        policy_version_id=policy_version_id,
        created_at=datetime.utcnow(),
    )
    db.add(audit)
