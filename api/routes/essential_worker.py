from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.cases import Case
from app.models.enums import CaseStatus
from app.models.policy_versions import PolicyVersion
from app.schemas.application import ApplicationCreate
from app.services.action_payload_builder import ActionExecutionContext, build_action_payload
from app.services.application_service import submit_application
from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from db.session import get_db
from app.models.essential_worker import EssentialWorkerBenefitMatch, EssentialWorkerProfile
from app.services.essential_worker_housing_service import (
    discover_housing_programs,
    generate_homebuyer_action_plan,
    generate_required_documents,
    upsert_worker_profile,
)


router = APIRouter(prefix="/essential-worker", tags=["Essential Worker Housing"])


class EssentialWorkerProfileRequest(BaseModel):
    case_id: UUID | None = None
    user_id: UUID | None = None
    profession: str
    employer_type: str | None = None
    state: str
    city: str | None = None
    annual_income: float | None = None
    first_time_homebuyer: str | None = None


class EssentialWorkerDiscoverRequest(BaseModel):
    case_id: UUID
    profile_id: UUID


class EssentialWorkerPublicIntakeRequest(BaseModel):
    profession: str
    employer_type: str | None = None
    state: str
    city: str | None = None
    annual_income: float | None = None
    first_time_homebuyer: str | None = None
    full_name: str
    contact_email: str
    phone: str
    consent_acknowledged: bool = False


@router.post("/profile")
def create_or_update_profile(
    request: EssentialWorkerProfileRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if request.case_id:
        PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="essential_worker.profile")
    profile = upsert_worker_profile(db, payload=request.model_dump(exclude_none=True), actor_id=user.id)
    db.commit()
    return {"profile_id": str(profile.id), "profession": profile.profession, "state": profile.state}


@router.post("/discover-benefits")
def discover_benefits(
    request: EssentialWorkerDiscoverRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="essential_worker.discover")
    result = discover_housing_programs(db, profile_id=request.profile_id)
    db.commit()
    return result


@router.post("/action-plan")
def action_plan(
    request: EssentialWorkerDiscoverRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="essential_worker.action_plan")
    plan = generate_homebuyer_action_plan(db, profile_id=request.profile_id)
    docs = generate_required_documents(db, profile_id=request.profile_id)
    return {"action_plan": plan["steps"], "required_documents": docs["documents"]}


@router.post("/intake/public")
def submit_public_essential_worker_intake(
    request: EssentialWorkerPublicIntakeRequest,
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
            program_key="essential_worker_housing",
            answers_json={"consent_acknowledged": request.consent_acknowledged},
        ),
    )

    case = _auto_create_case(
        db,
        case_type="essential_worker_intelligence",
        case_meta={
            "intake_source": "public_help_essential_worker",
            "full_name": request.full_name,
            "contact_email": request.contact_email.strip(),
            "phone": request.phone,
            "consent_acknowledged": request.consent_acknowledged,
        },
    )

    profile = upsert_worker_profile(
        db,
        payload={
            "case_id": case.id,
            "profession": request.profession,
            "employer_type": request.employer_type,
            "state": request.state,
            "city": request.city,
            "annual_income": request.annual_income,
            "first_time_homebuyer": request.first_time_homebuyer,
        },
        actor_id=None,
    )
    db.commit()

    return {
        "status": "submitted",
        "case_id": str(case.id),
        "profile_id": str(profile.id),
        "message": "Essential worker intake submitted. A housing specialist will review your options within 1 business day.",
    }


@router.get("/workspace/cases")
def get_essential_worker_workspace_cases(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    rows = (
        db.query(Case, EssentialWorkerProfile)
        .join(EssentialWorkerProfile, EssentialWorkerProfile.case_id == Case.id)
        .order_by(Case.created_at.desc())
        .limit(200)
        .all()
    )

    return [
        {
            "case_id": str(case.id),
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "profile_id": str(profile.id),
            "profession": profile.profession,
            "state": profile.state,
            "city": profile.city,
            "annual_income": profile.annual_income,
            "contact_email": (case.meta or {}).get("contact_email"),
        }
        for case, profile in rows
    ]


@router.get("/workspace/cases/{case_id}")
def get_essential_worker_workspace_case_detail(
    case_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    case = db.query(Case).filter(Case.id == case_id).first()
    profile = db.query(EssentialWorkerProfile).filter(EssentialWorkerProfile.case_id == case_id).first()
    if not case or not profile:
        raise HTTPException(status_code=404, detail="Essential worker case not found")

    audits = (
        db.query(AuditLog)
        .filter(AuditLog.case_id == case_id)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )
    programs = (
        db.query(EssentialWorkerBenefitMatch)
        .filter(EssentialWorkerBenefitMatch.profile_id == profile.id)
        .order_by(EssentialWorkerBenefitMatch.estimated_value.desc())
        .all()
    )

    return {
        "case_id": str(case.id),
        "status": case.status.value if case.status else None,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "meta": case.meta or {},
        "profile": {
            "profile_id": str(profile.id),
            "profession": profile.profession,
            "employer_type": profile.employer_type,
            "state": profile.state,
            "city": profile.city,
            "annual_income": profile.annual_income,
            "first_time_homebuyer": profile.first_time_homebuyer,
        },
        "eligible_programs": [
            {"program": row.program, "estimated_value": row.estimated_value, "details": row.details or {}}
            for row in programs
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


@router.post("/workspace/cases/{case_id}/actions/discover-programs")
def workspace_discover_programs(
    case_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = build_action_payload(
        "discover_housing_programs",
        {"case_id": str(case_id)},
        context=ActionExecutionContext(case_id=case_id, actor_id=user.id),
    )
    profile = db.query(EssentialWorkerProfile).filter(EssentialWorkerProfile.case_id == case_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Essential worker profile not found")

    result = discover_housing_programs(db, profile_id=profile.id)
    db.commit()
    return {"case_id": str(case_id), **result}


@router.post("/workspace/cases/{case_id}/actions/generate-plan")
def workspace_generate_plan(
    case_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = build_action_payload(
        "generate_homebuyer_action_plan",
        {"case_id": str(case_id)},
        context=ActionExecutionContext(case_id=case_id, actor_id=user.id),
    )
    profile = db.query(EssentialWorkerProfile).filter(EssentialWorkerProfile.case_id == case_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Essential worker profile not found")

    plan = generate_homebuyer_action_plan(db, profile_id=profile.id)
    docs = generate_required_documents(db, profile_id=profile.id)
    return {
        "case_id": str(case_id),
        "steps": plan["steps"],
        "required_documents": docs["documents"],
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
