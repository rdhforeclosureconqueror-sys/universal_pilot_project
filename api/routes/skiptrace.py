from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from db.session import get_db
from app.models.audit_logs import AuditLog
from app.models.cases import Case
from app.models.housing_intelligence import ForeclosureCaseData
from app.services.skiptrace_service import skiptrace_case_owner


router = APIRouter(prefix="/skiptrace", tags=["Skiptrace Workspace"])


class SkiptraceActionRequest(BaseModel):
    provider: str = "batchdata"


class ConfirmSkiptraceRequest(BaseModel):
    owner_name: str | None = None
    phone: str | None = None
    email: str | None = None


@router.get("/workspace/cases")
def get_skiptrace_workspace_cases(
    search: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    rows = (
        db.query(Case, ForeclosureCaseData)
        .join(ForeclosureCaseData, ForeclosureCaseData.case_id == Case.id)
        .order_by(Case.created_at.desc())
        .limit(200)
        .all()
    )

    normalized_search = (search or "").strip().lower()
    items = []
    for case, profile in rows:
        address = (profile.property_address or "").strip()
        owner_hint = ((case.meta or {}).get("full_name") or (case.meta or {}).get("owner_name") or "").strip()
        if normalized_search:
            haystack = " ".join([
                str(case.id),
                address,
                profile.city or "",
                profile.state or "",
                owner_hint,
            ]).lower()
            if normalized_search not in haystack:
                continue
        items.append(
            {
                "case_id": str(case.id),
                "property_address": address,
                "city": profile.city,
                "state": profile.state,
                "owner_hint": owner_hint,
                "foreclosure_stage": profile.foreclosure_stage,
                "created_at": case.created_at.isoformat() if case.created_at else None,
            }
        )

    return items


@router.get("/workspace/cases/{case_id}")
def get_skiptrace_workspace_case_detail(
    case_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    case = db.query(Case).filter(Case.id == case_id).first()
    profile = db.query(ForeclosureCaseData).filter(ForeclosureCaseData.case_id == case_id).first()
    if not case or not profile:
        raise HTTPException(status_code=404, detail="Skiptrace case not found")

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.case_id == case_id)
        .filter(AuditLog.action_type.in_(["skiptrace_run", "skiptrace_retry", "skiptrace_confirmed"]))
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )

    latest_result = next((row for row in logs if row.action_type in {"skiptrace_run", "skiptrace_retry"}), None)
    current_result = (latest_result.after_state or {}).get("result") if latest_result else None

    return {
        "case_id": str(case.id),
        "property": {
            "address": profile.property_address,
            "city": profile.city,
            "state": profile.state,
            "zip_code": profile.zip_code,
            "foreclosure_stage": profile.foreclosure_stage,
        },
        "owner_hint": ((case.meta or {}).get("full_name") or (case.meta or {}).get("owner_name")),
        "current_result": current_result,
        "history": [
            {
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "action_type": row.action_type,
                "reason_code": row.reason_code,
                "provider": (row.after_state or {}).get("provider"),
                "result": (row.after_state or {}).get("result") if row.action_type in {"skiptrace_run", "skiptrace_retry"} else None,
                "confirmed_contact": (row.after_state or {}).get("confirmed_contact") if row.action_type == "skiptrace_confirmed" else None,
            }
            for row in logs
        ],
    }


@router.post("/workspace/cases/{case_id}/actions/run")
def run_skiptrace(
    case_id: UUID,
    request: SkiptraceActionRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    profile = db.query(ForeclosureCaseData).filter(ForeclosureCaseData.case_id == case_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Skiptrace case not found")

    result = skiptrace_case_owner(case_id=case_id, address=profile.property_address, provider=request.provider)
    db.add(
        AuditLog(
            id=uuid4(),
            case_id=case_id,
            actor_id=user.id,
            actor_is_ai=False,
            action_type="skiptrace_run",
            reason_code="skiptrace_lookup_started",
            before_state={},
            after_state={"provider": request.provider, "result": result},
            policy_version_id=None,
        )
    )
    db.commit()

    return {"case_id": str(case_id), "provider": request.provider, "result": result}


@router.post("/workspace/cases/{case_id}/actions/retry")
def retry_skiptrace(
    case_id: UUID,
    request: SkiptraceActionRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    profile = db.query(ForeclosureCaseData).filter(ForeclosureCaseData.case_id == case_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Skiptrace case not found")

    result = skiptrace_case_owner(case_id=case_id, address=profile.property_address, provider=request.provider)
    db.add(
        AuditLog(
            id=uuid4(),
            case_id=case_id,
            actor_id=user.id,
            actor_is_ai=False,
            action_type="skiptrace_retry",
            reason_code="skiptrace_lookup_retried",
            before_state={},
            after_state={"provider": request.provider, "result": result},
            policy_version_id=None,
        )
    )
    db.commit()

    return {"case_id": str(case_id), "provider": request.provider, "result": result}


@router.post("/workspace/cases/{case_id}/actions/confirm")
def confirm_skiptrace_result(
    case_id: UUID,
    request: ConfirmSkiptraceRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Skiptrace case not found")

    confirmed_contact = {
        "owner_name": request.owner_name,
        "phone": request.phone,
        "email": request.email,
    }

    db.add(
        AuditLog(
            id=uuid4(),
            case_id=case_id,
            actor_id=user.id,
            actor_is_ai=False,
            action_type="skiptrace_confirmed",
            reason_code="skiptrace_contact_confirmed",
            before_state={"meta": case.meta or {}},
            after_state={"confirmed_contact": confirmed_contact},
            policy_version_id=None,
        )
    )

    next_meta = dict(case.meta or {})
    next_meta["confirmed_contact"] = confirmed_contact
    case.meta = next_meta
    db.commit()

    return {"case_id": str(case_id), "confirmed_contact": confirmed_contact, "status": "confirmed"}
