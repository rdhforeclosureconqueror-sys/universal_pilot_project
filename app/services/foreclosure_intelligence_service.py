from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.housing_intelligence import ForeclosureCaseData


def create_foreclosure_profile(
    db: Session,
    *,
    case_id: UUID | None,
    payload: dict,
    actor_id: UUID | None
) -> ForeclosureCaseData:

    # ---------------------------------------------------
    # Auto-create case_id if not provided
    # ---------------------------------------------------

    if not case_id:
        case_id = uuid4()

    # ---------------------------------------------------
    # Check if profile already exists
    # ---------------------------------------------------

    profile = (
        db.query(ForeclosureCaseData)
        .filter(ForeclosureCaseData.case_id == case_id)
        .first()
    )

    if profile:
        raise HTTPException(
            status_code=409,
            detail="Foreclosure profile already exists for case"
        )

    # ---------------------------------------------------
    # Create foreclosure profile
    # ---------------------------------------------------

    profile = ForeclosureCaseData(
        id=uuid4(),
        case_id=case_id,
        property_address=payload.get("property_address"),
        city=payload.get("city"),
        state=payload.get("state"),
        loan_balance=payload.get("loan_balance"),
        estimated_property_value=payload.get("estimated_property_value"),
        arrears_amount=payload.get("arrears_amount"),
        homeowner_income=payload.get("homeowner_income"),
        foreclosure_stage=payload.get("foreclosure_stage", "pre_foreclosure"),
    )

    db.add(profile)
    db.flush()

    # ---------------------------------------------------
    # Audit log
    # ---------------------------------------------------

    _audit(
        db,
        actor_id=actor_id,
        case_id=case_id,
        action_type="foreclosure_profile_created",
        reason_code="foreclosure_profile_created",
        after_state={"profile_id": str(profile.id)},
    )

    return profile


def update_foreclosure_status(
    db: Session,
    *,
    case_id: UUID,
    foreclosure_stage: str,
    actor_id: UUID | None
) -> ForeclosureCaseData:

    profile = (
        db.query(ForeclosureCaseData)
        .filter(ForeclosureCaseData.case_id == case_id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Foreclosure profile not found"
        )

    before = profile.foreclosure_stage
    profile.foreclosure_stage = foreclosure_stage

    db.flush()

    _audit(
        db,
        actor_id=actor_id,
        case_id=case_id,
        action_type="foreclosure_status_updated",
        reason_code="foreclosure_stage_updated",
        after_state={
            "before_stage": before,
            "after_stage": foreclosure_stage
        },
    )

    return profile


def calculate_case_priority(db: Session, *, case_id: UUID) -> dict:

    profile = (
        db.query(ForeclosureCaseData)
        .filter(ForeclosureCaseData.case_id == case_id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Foreclosure profile not found"
        )

    stage = (profile.foreclosure_stage or "").lower()

    stage_weight = {
        "pre_foreclosure": 15,
        "notice_of_default": 30,
        "auction_scheduled": 50,
        "post_sale": 80,
    }.get(stage, 10)

    arrears = float(profile.arrears_amount or 0)
    income = float(profile.homeowner_income or 0)

    pressure = 0
    if income > 0:
        pressure = min(40, (arrears / income) * 10)

    score = min(100, stage_weight + pressure)

    if score >= 70:
        tier = "critical"
    elif score >= 40:
        tier = "high"
    else:
        tier = "standard"

    return {
        "case_id": str(case_id),
        "priority_score": round(score, 2),
        "priority_tier": tier,
    }


def _audit(
    db: Session,
    *,
    actor_id: UUID | None,
    case_id: UUID,
    action_type: str,
    reason_code: str,
    after_state: dict
) -> None:

    db.add(
        AuditLog(
            id=uuid4(),
            case_id=case_id,
            actor_id=actor_id,
            actor_is_ai=False,
            action_type=action_type,
            reason_code=reason_code,
            before_state={},
            after_state=after_state,
            policy_version_id=None,
        )
    )
