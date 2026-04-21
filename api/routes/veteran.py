from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.cases import Case
from app.models.enums import CaseStatus
from app.models.policy_versions import PolicyVersion
from app.models.veteran_intelligence import BenefitProgress, VeteranProfile
from app.schemas.application import ApplicationCreate
from app.services.action_payload_builder import ActionExecutionContext, build_action_payload
from app.services.application_service import submit_application
from app.services.veteran_intelligence_service import (
    calculate_benefit_value,
    generate_action_plan,
    match_benefits,
    upsert_veteran_profile,
)
from auth.dependencies import get_current_user
from db.session import get_db


router = APIRouter(prefix="/veteran", tags=["Veteran Intelligence"])


class VeteranPublicIntakeRequest(BaseModel):
    branch_of_service: str | None = None
    years_of_service: int | None = None
    discharge_status: str | None = None
    disability_rating: int | None = None
    permanent_and_total_status: bool = False
    combat_service: bool = False
    dependent_status: bool = False
    state_of_residence: str
    homeowner_status: bool = False
    mortgage_status: str | None = None
    foreclosure_risk: bool = False
    income_level: str | None = None
    full_name: str
    contact_email: str
    phone: str
    consent_acknowledged: bool = False


class VeteranProfileRequest(BaseModel):
    case_id: UUID
    branch_of_service: str | None = None
    years_of_service: int | None = None
    discharge_status: str | None = None
    disability_rating: int | None = None
    permanent_and_total_status: bool = False
    combat_service: bool = False
    dependent_status: bool = False
    state_of_residence: str | None = None
    homeowner_status: bool = False
    mortgage_status: str | None = None
    foreclosure_risk: bool = False
    income_level: str | None = None


@router.post("/profile")
def create_or_update_profile(
    request: VeteranProfileRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    payload = build_action_payload(
        "upsert_veteran_profile",
        request.model_dump(exclude_none=True),
        context=ActionExecutionContext(case_id=request.case_id, actor_id=user.id),
    )
    profile = upsert_veteran_profile(db, actor_id=user.id, payload=payload)
    db.commit()
    return {"case_id": str(profile.case_id), "profile_id": str(profile.id)}


@router.post("/intake/public")
def submit_public_veteran_intake(
    request: VeteranPublicIntakeRequest,
    db: Session = Depends(get_db),
):
    if not request.contact_email.strip():
        raise HTTPException(status_code=422, detail="contact_email is required")

    submit_application(
        db,
        ApplicationCreate(
            email=request.contact_email.strip(),
            full_name=request.full_name,
            phone=request.phone,
            program_key="veteran_intelligence",
            answers_json={"consent_acknowledged": request.consent_acknowledged},
        ),
    )

    case = _auto_create_case(
        db,
        case_type="veteran_intelligence",
        case_meta={
            "intake_source": "public_help_veteran",
            "full_name": request.full_name,
            "contact_email": request.contact_email.strip(),
            "phone": request.phone,
            "consent_acknowledged": request.consent_acknowledged,
        },
    )

    profile = upsert_veteran_profile(
        db,
        actor_id=None,
        payload={
            "case_id": str(case.id),
            "branch_of_service": request.branch_of_service,
            "years_of_service": request.years_of_service,
            "discharge_status": request.discharge_status,
            "disability_rating": request.disability_rating,
            "permanent_and_total_status": request.permanent_and_total_status,
            "combat_service": request.combat_service,
            "dependent_status": request.dependent_status,
            "state_of_residence": request.state_of_residence,
            "homeowner_status": request.homeowner_status,
            "mortgage_status": request.mortgage_status,
            "foreclosure_risk": request.foreclosure_risk,
            "income_level": request.income_level,
        },
    )
    db.commit()

    return {
        "status": "submitted",
        "case_id": str(case.id),
        "profile_id": str(profile.id),
        "message": "Veteran intake submitted. A benefits specialist will review your case within 1 business day.",
    }


@router.get("/workspace/cases")
def get_veteran_workspace_cases(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    rows = (
        db.query(Case, VeteranProfile)
        .join(VeteranProfile, VeteranProfile.case_id == Case.id)
        .order_by(Case.created_at.desc())
        .limit(200)
        .all()
    )

    return [
        {
            "case_id": str(case.id),
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "branch_of_service": profile.branch_of_service,
            "state_of_residence": profile.state_of_residence,
            "disability_rating": profile.disability_rating,
            "foreclosure_risk": profile.foreclosure_risk,
            "contact_email": (case.meta or {}).get("contact_email"),
        }
        for case, profile in rows
    ]


@router.get("/workspace/cases/{case_id}")
def get_veteran_workspace_case_detail(
    case_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    case = db.query(Case).filter(Case.id == case_id).first()
    profile = db.query(VeteranProfile).filter(VeteranProfile.case_id == case_id).first()
    if not case or not profile:
        raise HTTPException(status_code=404, detail="Veteran case not found")

    audits = (
        db.query(AuditLog)
        .filter(AuditLog.case_id == case_id)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )
    progress = (
        db.query(BenefitProgress)
        .filter(BenefitProgress.case_id == case_id)
        .order_by(BenefitProgress.updated_at.desc())
        .all()
    )

    return {
        "case_id": str(case.id),
        "status": case.status.value if case.status else None,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "meta": case.meta or {},
        "profile": {
            "branch_of_service": profile.branch_of_service,
            "years_of_service": profile.years_of_service,
            "discharge_status": profile.discharge_status,
            "disability_rating": profile.disability_rating,
            "permanent_and_total_status": profile.permanent_and_total_status,
            "combat_service": profile.combat_service,
            "dependent_status": profile.dependent_status,
            "state_of_residence": profile.state_of_residence,
            "homeowner_status": profile.homeowner_status,
            "mortgage_status": profile.mortgage_status,
            "foreclosure_risk": profile.foreclosure_risk,
            "income_level": profile.income_level,
        },
        "benefit_progress": [
            {
                "benefit_name": row.benefit_name,
                "status": row.status,
                "status_notes": row.status_notes,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in progress
        ],
        "audit_log": [
            {
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "action_type": row.action_type,
                "reason_code": row.reason_code,
            }
            for row in audits
        ],
    }


@router.post("/workspace/cases/{case_id}/actions/discover-benefits")
def workspace_discover_benefits(
    case_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = build_action_payload(
        "scan_veteran_benefits",
        {"case_id": str(case_id)},
        context=ActionExecutionContext(case_id=case_id, actor_id=user.id),
    )
    result = match_benefits(db, case_id=case_id)
    value = calculate_benefit_value(db, case_id=case_id)
    db.commit()
    return {
        "case_id": str(case_id),
        "eligible_benefits": result.get("eligible_benefits", []),
        "estimated_total_value": value.get("annual_total", 0),
        "categories": result.get("categories", []),
    }


@router.post("/workspace/cases/{case_id}/actions/generate-plan")
def workspace_generate_plan(
    case_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = build_action_payload(
        "generate_veteran_action_plan",
        {"case_id": str(case_id)},
        context=ActionExecutionContext(case_id=case_id, actor_id=user.id),
    )
    plan = generate_action_plan(db, case_id=case_id)
    db.commit()
    return {
        "case_id": str(case_id),
        "steps": plan.get("steps", []),
        "match_summary": plan.get("match_summary", {}),
    }


def _auto_create_case(db: Session, *, case_type: str, case_meta: dict | None = None) -> Case:
    policy = (
        db.query(PolicyVersion)
        .filter(PolicyVersion.is_active.is_(True))
        .order_by(PolicyVersion.created_at.desc())
        .first()
    )

    if not policy:
        raise HTTPException(status_code=400, detail="No active policy available to initialize case")

    actor_id = _resolve_case_actor_id(db)
    if not actor_id:
        raise HTTPException(status_code=400, detail="No available system actor to initialize case")

    case = Case(
        status=CaseStatus.intake_submitted,
        created_by=actor_id,
        program_type=policy.program_key,
        program_key=policy.program_key,
        case_type=case_type,
        meta=case_meta or {},
        policy_version_id=policy.id,
    )
    db.add(case)
    db.flush()
    return case


def _resolve_case_actor_id(db: Session) -> UUID | None:
    from app.models.users import User

    user = db.query(User).order_by(User.created_at.asc()).first()
    return user.id if user else None
