from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.essential_worker import EssentialWorkerBenefitMatch, EssentialWorkerProfile


PROGRAMS = {
    "nurse": [
        {"program": "Good Neighbor Next Door", "estimated_value": 150000},
        {"program": "Texas Homebuyer Assistance", "estimated_value": 15000},
    ],
    "teacher": [
        {"program": "Good Neighbor Next Door", "estimated_value": 120000},
        {"program": "Teacher Next Door", "estimated_value": 10000},
    ],
    "police": [{"program": "Hero Housing Assistance", "estimated_value": 20000}],
    "firefighter": [{"program": "Hero Housing Assistance", "estimated_value": 20000}],
    "emt": [{"program": "Community Responder Housing Fund", "estimated_value": 12000}],
    "healthcare": [{"program": "Healthcare Worker Homebuyer Grant", "estimated_value": 15000}],
}


def upsert_worker_profile(db: Session, *, payload: dict, actor_id: UUID | None) -> EssentialWorkerProfile:
    case_id = payload.get("case_id")
    profile = None
    if case_id:
        profile = db.query(EssentialWorkerProfile).filter(EssentialWorkerProfile.case_id == case_id).first()

    if not profile:
        profile = EssentialWorkerProfile(**payload)
        db.add(profile)
    else:
        for k, v in payload.items():
            setattr(profile, k, v)
    db.flush()

    if profile.case_id:
        _audit(db, case_id=profile.case_id, actor_id=actor_id, action_type="essential_worker_profile_upserted", reason_code="essential_worker_profile_saved")
    return profile


def discover_housing_programs(db: Session, *, profile_id: UUID) -> dict:
    profile = db.query(EssentialWorkerProfile).filter(EssentialWorkerProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Essential worker profile not found")

    programs = PROGRAMS.get((profile.profession or "").lower(), [])
    db.query(EssentialWorkerBenefitMatch).filter(EssentialWorkerBenefitMatch.profile_id == profile.id).delete()
    for p in programs:
        db.add(EssentialWorkerBenefitMatch(profile_id=profile.id, program=p["program"], estimated_value=float(p["estimated_value"]), details={"state": profile.state}))
    db.flush()

    return {
        "eligible_programs": programs,
        "total_estimated_benefits": round(sum(float(p["estimated_value"]) for p in programs), 2),
    }


def calculate_assistance_value(db: Session, *, profile_id: UUID) -> dict:
    matches = db.query(EssentialWorkerBenefitMatch).filter(EssentialWorkerBenefitMatch.profile_id == profile_id).all()
    total = round(sum(float(m.estimated_value or 0) for m in matches), 2)
    return {"profile_id": str(profile_id), "total_estimated_benefits": total}


def generate_homebuyer_action_plan(db: Session, *, profile_id: UUID) -> dict:
    matches = db.query(EssentialWorkerBenefitMatch).filter(EssentialWorkerBenefitMatch.profile_id == profile_id).all()
    steps = ["Validate employment certification", "Check credit and lender pre-approval"]
    for m in matches:
        steps.append(f"Apply for {m.program}")
    return {"profile_id": str(profile_id), "steps": steps}


def generate_required_documents(db: Session, *, profile_id: UUID) -> dict:
    _ = db
    return {
        "profile_id": str(profile_id),
        "documents": [
            "Employment verification letter",
            "Income documentation package",
            "Program-specific grant application",
        ],
    }


def _audit(db: Session, *, case_id: UUID, actor_id: UUID | None, action_type: str, reason_code: str) -> None:
    db.add(
        AuditLog(
            id=uuid4(),
            case_id=case_id,
            actor_id=actor_id,
            actor_is_ai=False,
            action_type=action_type,
            reason_code=reason_code,
            before_state={},
            after_state={},
            policy_version_id=None,
        )
    )
