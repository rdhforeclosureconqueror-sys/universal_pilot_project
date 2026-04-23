# api/routes/cases.py

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from audit.logger import log_audit
from db.session import get_db
from app.models.cases import Case
from app.models.enums import CaseStatus
from app.models.policy_versions import PolicyVersion
from app.schemas.case import CaseCreateRequest
from app.services.workflow_engine import initialize_case_workflow, sync_case_workflow

router = APIRouter()


def _resolve_allowed_meta_fields(policy_config: dict) -> list[str]:
    return (
        policy_config.get("allowed_meta_fields")
        or policy_config.get("allowed_fields")
        or policy_config.get("custom_fields")
        or []
    )


def _validate_meta_fields_or_422(*, incoming_meta: dict, policy_config: dict) -> None:
    allowed_fields = _resolve_allowed_meta_fields(policy_config)
    for field in incoming_meta.keys():
        if field not in allowed_fields:
            raise HTTPException(
                status_code=422,
                detail=f"Field '{field}' not allowed by policy",
            )


@router.post("/cases")
def create_case(case_data: CaseCreateRequest, db: Session = Depends(get_db)):
    case_id = uuid4()
    now = datetime.utcnow()

    policy = (
        db.query(PolicyVersion)
        .filter(
            PolicyVersion.program_key == case_data.program_key,
            PolicyVersion.is_active == True,
        )
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=400,
            detail="Active policy not found for program",
        )

    incoming_meta = case_data.meta or {}

    # Validate allowed custom fields
    _validate_meta_fields_or_422(incoming_meta=incoming_meta, policy_config=policy.config_json or {})

    # Dedupe check
    dedupe_key = policy.config_json.get("dedupe_check")
    if dedupe_key:
        hash_val = incoming_meta.get(dedupe_key)
        if hash_val:
            exists = (
                db.query(Case)
                .filter(Case.meta[dedupe_key].astext == hash_val)
                .first()
            )
            if exists:
                raise HTTPException(
                    status_code=409,
                    detail="Duplicate opportunity case detected",
                )

    # Determine initial status
    status = (
        CaseStatus.intake_incomplete
        if policy.config_json.get("review_required")
        else CaseStatus.intake_submitted
    )

    new_case = Case(
        id=case_id,
        status=status,
        program_type=case_data.program_key,
        program_key=case_data.program_key,
        created_by=UUID(case_data.created_by),
        meta=incoming_meta,
        created_at=now,
        policy_version_id=policy.id,
    )

    db.add(new_case)

    log_audit(
        db=db,
        case_id=case_id,
        actor_id=UUID(case_data.created_by),
        action_type="case_created",
        reason_code="intake_received",
        before_json={},
        after_json={
            "status": status.value,
            "meta": incoming_meta,
        },
        policy_version_id=policy.id,
    )

    db.flush()

    initialize_case_workflow(db, new_case.id)
    sync_case_workflow(db, new_case.id)

    db.commit()
    db.refresh(new_case)

    return {
        "id": str(new_case.id),
        "status": new_case.status.value,
    }


@router.get("/cases")
def list_cases(
    status: CaseStatus | None = Query(default=None),
    program_key: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Case)

    if status is not None:
        query = query.filter(Case.status == status)
    if program_key is not None:
        query = query.filter(Case.program_key == program_key)
    if created_from is not None:
        query = query.filter(Case.created_at >= created_from)
    if created_to is not None:
        query = query.filter(Case.created_at <= created_to)

    cases = query.order_by(Case.created_at.desc()).all()
    return [
        {
            "id": str(case.id),
            "program_key": case.program_key,
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "status": case.status.value if case.status else None,
            "meta": case.meta or {},
        }
        for case in cases
    ]
