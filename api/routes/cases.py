# api/routes/cases.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from db.session import get_db
from models.cases import Case
from models.policy_versions import PolicyVersion
from schemas.case import CaseCreateRequest
from audit.logger import log_audit

router = APIRouter()

@router.post("/cases")
def create_case(case_data: CaseCreateRequest, db: Session = Depends(get_db)):
    case_id = str(uuid4())
    now = datetime.utcnow()

    # Load active policy for the program
    policy = (
        db.query(PolicyVersion)
        .filter(PolicyVersion.program_key == case_data.program_key, PolicyVersion.is_active == True)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=400, detail="Active policy not found for program")

    incoming_meta = case_data.meta or {}

    # ✅ Enforce custom field validation from policy
    custom_fields = policy.config_json.get("custom_fields", [])
    for field in incoming_meta.keys():
        if field not in custom_fields:
            raise HTTPException(status_code=422, detail=f"Field '{field}' not allowed by policy")

    # ✅ Enforce deduplication logic if configured in policy
    dedupe_key = policy.config_json.get("dedupe_check")
    if dedupe_key:
        hash_val = incoming_meta.get(dedupe_key)
        if hash_val:
            exists = db.query(Case).filter(Case.meta[dedupe_key].astext == hash_val).first()
            if exists:
                raise HTTPException(status_code=409, detail="Duplicate opportunity case detected")

    # ✅ Determine case status based on review requirement
    status = "intake_incomplete" if policy.config_json.get("review_required") else "intake_submitted"

    # ✅ Create the new case
    new_case = Case(
        id=case_id,
        status=status,
        program_key=case_data.program_key,
        program_type=case_data.program_key,
        created_by=case_data.created_by,
        meta=incoming_meta,
        created_at=now,
        policy_version_id=policy.id
    )
    db.add(new_case)

    # ✅ Log audit for case creation
    log_audit(
        db=db,
        case_id=case_id,
        actor_id=case_data.created_by,
        action_type="case_created",
        reason_code="intake_received",
        before_state={},
        after_state={"status": status, "meta": incoming_meta},
        policy_version_id=policy.id
    )

    db.commit()
    db.refresh(new_case)

    return {"id": new_case.id, "status": new_case.status}
