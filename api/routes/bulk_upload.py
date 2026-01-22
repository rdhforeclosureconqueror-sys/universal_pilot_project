# api/routes/bulk_upload.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from db.session import get_db
from models.cases import Case
from models.policy_versions import PolicyVersion
from schemas.bulk_upload import BulkUploadRequest, SingleCaseDraft
from audit.logger import log_audit

router = APIRouter()

@router.post("/cases/bulk_upload")
def bulk_upload_cases(payload: BulkUploadRequest, db: Session = Depends(get_db)):
    created_case_ids = []
    now = datetime.utcnow()

    # Fetch active policy version for the given program
    policy = (
        db.query(PolicyVersion)
        .filter(PolicyVersion.program_key == payload.program_key, PolicyVersion.is_active == True)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=400, detail="Active policy not found for program")

    for entry in payload.cases:
        # Validate required fields
        required_fields = ["first_name", "zip_code", "source_organization"]
        for field in required_fields:
            if not entry.meta.get(field):
                raise HTTPException(status_code=422, detail=f"Missing required field: {field}")

        # Deduplication check (by contact or source_upload_id)
        contact_hash = entry.meta.get("contact_hash")
        source_upload_id = entry.meta.get("source_upload_id")

        if contact_hash:
            exists = db.query(Case).filter(Case.meta["contact_hash"].astext == contact_hash).first()
            if exists:
                continue  # Skip duplicate

        if source_upload_id:
            exists = db.query(Case).filter(Case.meta["source_upload_id"].astext == source_upload_id).first()
            if exists:
                continue  # Skip duplicate

        case_id = str(uuid4())

        new_case = Case(
            id=case_id,
            status="intake_incomplete",
            program_key=payload.program_key,
            meta=entry.meta,
            created_at=now,
            policy_version_id=policy.id
        )
        db.add(new_case)

        # Log audit
        log_audit(
            db=db,
            case_id=case_id,
            actor_id=payload.created_by,
            action_type="bulk_upload_draft_created",
            reason_code="partner_batch_intake",
            before_state={},
            after_state={"status": "intake_incomplete"},
            policy_version_id=policy.id
        )

        created_case_ids.append(case_id)

    db.commit()

    return {"created_case_ids": created_case_ids}
