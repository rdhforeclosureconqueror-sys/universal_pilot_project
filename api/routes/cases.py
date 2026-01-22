from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models.cases import Case, CaseStatus
from models.audit_logs import AuditLog
from auth.dependencies import get_current_user
from db.session import get_db
from policy.loader import PolicyEngine
import uuid
from datetime import datetime

router = APIRouter(prefix="/cases", tags=["Cases"])

# 🔧 Status transition logic
VALID_TRANSITIONS = {
    "intake_submitted": ["under_review", "intake_incomplete", "case_closed_other_outcome"],
    "intake_incomplete": ["under_review", "case_closed_other_outcome"],
    "under_review": ["in_progress", "intake_incomplete", "case_closed_other_outcome"],
    "in_progress": ["program_completed_positive_outcome", "case_closed_other_outcome"],
}

TERMINAL_STATES = ["program_completed_positive_outcome", "case_closed_other_outcome"]

def is_valid_transition(current: str, new: str) -> bool:
    if current in TERMINAL_STATES:
        return False
    return new in VALID_TRANSITIONS.get(current, [])

# 📦 Payload schemas
class CaseCreate(BaseModel):
    program_type: str | None = None
    meta: dict | None = None  # ✅ Add support for incoming meta

class StatusUpdate(BaseModel):
    new_status: CaseStatus
    reason_code: str

# 🚀 POST /cases
@router.post("/", status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    policy_engine = PolicyEngine(db)
    
    # 🔁 Use correct program_type for active policy
    program_key = payload.program_type or "default_program"
    policy = policy_engine.get_active_policy(program_key=program_key)

    # ✅ Validate meta fields using policy-defined custom_fields
    incoming_meta = payload.meta or {}
    custom_fields = policy.config_json.get("custom_fields", [])
    for field in incoming_meta.keys():
        if field not in custom_fields:
            raise HTTPException(status_code=422, detail=f"Field '{field}' not allowed by policy")

    # ✅ Create the case with meta
    case = Case(
        id=uuid.uuid4(),
        status=CaseStatus.intake_submitted,
        program_type=payload.program_type,
        policy_version_id=policy.id,
        created_by=user.id,
        meta=incoming_meta  # ✅ Save meta to DB
    )
    db.add(case)

    audit = AuditLog(
        id=uuid.uuid4(),
        case_id=case.id,
        actor_id=user.id,
        action_type="case_created",
        reason_code="intake_received",
        before_state={},
        after_state={"status": case.status},
        created_at=datetime.utcnow()
    )
    db.add(audit)

    db.commit()
    db.refresh(case)

    return {"case_id": case.id, "status": case.status}

# 🔄 PATCH /cases/{id}/status
@router.patch("/{case_id}/status")
def update_status(case_id: str, payload: StatusUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not is_valid_transition(case.status, payload.new_status):
        audit = AuditLog(
            id=uuid.uuid4(),
            case_id=case.id,
            actor_id=user.id,
            action_type="case_state_change_blocked",
            reason_code="transition_forbidden",
            before_state={"status": case.status},
            after_state={"attempted": payload.new_status},
            created_at=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
        raise HTTPException(status_code=409, detail="Invalid status transition")

    before = case.status
    case.status = payload.new_status
    db.add(case)

    audit = AuditLog(
        id=uuid.uuid4(),
        case_id=case.id,
        actor_id=user.id,
        action_type="case_state_change",
        reason_code=payload.reason_code,
        before_state={"status": before},
        after_state={"status": case.status},
        created_at=datetime.utcnow()
    )
    db.add(audit)

    db.commit()
    return {"case_id": case.id, "status": case.status}
