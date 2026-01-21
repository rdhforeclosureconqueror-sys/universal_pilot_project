from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models.cases import Case, CaseStatus
from models.audit_logs import AuditLog
from auth.dependencies import get_current_user
from db.session import get_db
import uuid
from datetime import datetime

router = APIRouter(prefix="/cases", tags=["Cases"])

class CaseCreate(BaseModel):
    program_type: str | None = None

@router.post("/", status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    case = Case(
        id=uuid.uuid4(),
        status=CaseStatus.intake_submitted,
        program_type=payload.program_type,
        created_by=user.id
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
