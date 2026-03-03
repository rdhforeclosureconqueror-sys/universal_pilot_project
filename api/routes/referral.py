from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.referrals import Referral
from app.models.consent_records import ConsentRecord
from app.models.outbox_queue import OutboxQueue
from app.models.audit_logs import AuditLog
from db.session import get_db
from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(prefix="/cases/{case_id}/referral", tags=["Referrals"])


class ReferralRequest(BaseModel):
    partner_id: str


@router.post("/", status_code=202)
def queue_referral(case_id: str, request: ReferralRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=case_id, action="referral.queue")

    consent = db.query(ConsentRecord).filter(
        ConsentRecord.case_id == case_id,
        ConsentRecord.revoked == False,
        ConsentRecord.scope.contains(["referral"])
    ).first()

    if not consent:
        audit = AuditLog(
            id=uuid4(),
            case_id=case_id,
            actor_id=user.id,
            action_type="referral_queue_blocked",
            reason_code="missing_consent_scope",
            before_state={},
            after_state={},
            created_at=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
        raise HTTPException(status_code=403, detail="Consent for referral not found")

    referral_id = uuid4()
    referral = Referral(
        id=referral_id,
        case_id=case_id,
        partner_id=request.partner_id,
        status="draft",
        created_at=datetime.utcnow()
    )
    db.add(referral)

    dedupe_key = f"referral:{case_id}:{request.partner_id}"
    existing = db.query(OutboxQueue).filter_by(dedupe_key=dedupe_key).first()
    if existing:
        raise HTTPException(status_code=409, detail="Duplicate referral attempt")

    outbox = OutboxQueue(
        id=uuid4(),
        event_type="send_referral",
        case_id=case_id,
        payload={"referral_id": str(referral_id), "partner_id": request.partner_id},
        dedupe_key=dedupe_key,
        attempts=0,
        max_attempts=3,
        created_at=datetime.utcnow()
    )
    db.add(outbox)

    audit = AuditLog(
        id=uuid4(),
        case_id=case_id,
        actor_id=user.id,
        action_type="referral_queued",
        reason_code="referral_granted_with_consent",
        before_state={},
        after_state={"referral_id": str(referral_id)},
        created_at=datetime.utcnow()
    )
    db.add(audit)

    db.commit()
    return {"status": "queued", "referral_id": str(referral_id)}
