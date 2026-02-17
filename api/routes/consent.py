from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.consent_records import ConsentRecord
from models.audit_logs import AuditLog
from db.session import get_db
from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/consent", tags=["Consent"])


class ConsentGrantRequest(BaseModel):
    case_id: str
    scope: List[str]


class ConsentRevokeRequest(BaseModel):
    case_id: str


@router.post("/", status_code=201)
def grant_consent(request: ConsentGrantRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=request.case_id, action="consent.grant")
    existing = db.query(ConsentRecord).filter(
        ConsentRecord.case_id == request.case_id,
        ConsentRecord.revoked == False
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Consent already granted")

    consent = ConsentRecord(
        id=uuid4(),
        case_id=request.case_id,
        granted_by_user_id=user.id,
        scope=request.scope,
        valid_from=datetime.utcnow(),
        revoked=False
    )
    db.add(consent)

    audit = AuditLog(
        id=uuid4(),
        case_id=request.case_id,
        actor_id=user.id,
        action_type="consent_granted",
        reason_code="consent_granted",
        before_state={},
        after_state={"scope": request.scope},
        created_at=datetime.utcnow()
    )
    db.add(audit)
    db.commit()
    return {"status": "consent_granted", "scope": request.scope}


@router.post("/revoke", status_code=200)
def revoke_consent(request: ConsentRevokeRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=request.case_id, action="consent.revoke")
    consent = db.query(ConsentRecord).filter(
        ConsentRecord.case_id == request.case_id,
        ConsentRecord.revoked == False
    ).first()

    if not consent:
        raise HTTPException(status_code=404, detail="No active consent to revoke")

    consent.revoked = True
    consent.revoked_at = datetime.utcnow()

    audit = AuditLog(
        id=uuid4(),
        case_id=request.case_id,
        actor_id=user.id,
        action_type="consent_revoked",
        reason_code="consent_revoked",
        before_state={"revoked": False},
        after_state={"revoked": True},
        created_at=datetime.utcnow()
    )
    db.add(audit)
    db.commit()
    return {"status": "consent_revoked", "case_id": request.case_id}
