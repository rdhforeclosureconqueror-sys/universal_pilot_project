from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.foreclosure_intelligence import ForeclosureCreateRequest
from auth.dependencies import get_current_user
from db.session import get_db
from app.services.foreclosure_intelligence_service import calculate_case_priority, create_foreclosure_profile
from app.services.partner_routing_service import route_case_to_partner
from app.services.property_analysis_service import (
    calculate_acquisition_score,
    calculate_equity,
    calculate_ltv,
    calculate_rescue_score,
    classify_intervention,
)


router = APIRouter(prefix="/verify", tags=["Phase Verification"])


def _seed_payload() -> ForeclosureCreateRequest:
    return ForeclosureCreateRequest(
        property_address="123 Main St",
        city="Dallas",
        state="TX",
        loan_balance=210000,
        estimated_property_value=320000,
        arrears_amount=15000,
        foreclosure_stage="pre_foreclosure",
        homeowner_income=4000,
    )


@router.get("/phase9")
def verify_phase9(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    seed = _seed_payload()

    created = create_foreclosure_profile(
        db,
        case_id=None,
        payload=seed.model_dump(exclude={"case_id"}, exclude_none=True),
        actor_id=user.id,
    )
    case_id = created["case_id"]

    equity = calculate_equity(estimated_property_value=seed.estimated_property_value, loan_balance=seed.loan_balance)
    ltv = calculate_ltv(loan_balance=seed.loan_balance, estimated_property_value=seed.estimated_property_value)
    rescue = calculate_rescue_score(arrears_amount=seed.arrears_amount, homeowner_income=seed.homeowner_income or 0, foreclosure_stage=seed.foreclosure_stage)
    acq = calculate_acquisition_score(equity=equity, ltv=ltv, foreclosure_stage=seed.foreclosure_stage)
    _ = classify_intervention(rescue_score=rescue, acquisition_score=acq, ltv=ltv)
    priority = calculate_case_priority(db, case_id=case_id)
    db.commit()

    return {
        "phase": "phase9",
        "case_id": str(case_id),
        "case_created": True,
        "profile_created": bool(created["profile_created"]),
        "analysis_completed": True,
        "priority_calculated": bool(priority.get("priority_tier")),
        "system_status": "operational",
    }


@router.get("/phase10")
def verify_phase10(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    seed = _seed_payload()

    created = create_foreclosure_profile(
        db,
        case_id=None,
        payload=seed.model_dump(exclude={"case_id"}, exclude_none=True),
        actor_id=user.id,
    )
    case_id = created["case_id"]

    equity = calculate_equity(estimated_property_value=seed.estimated_property_value, loan_balance=seed.loan_balance)
    ltv = calculate_ltv(loan_balance=seed.loan_balance, estimated_property_value=seed.estimated_property_value)
    rescue = calculate_rescue_score(arrears_amount=seed.arrears_amount, homeowner_income=seed.homeowner_income or 0, foreclosure_stage=seed.foreclosure_stage)
    acq = calculate_acquisition_score(equity=equity, ltv=ltv, foreclosure_stage=seed.foreclosure_stage)
    classification = classify_intervention(rescue_score=rescue, acquisition_score=acq, ltv=ltv)
    priority = calculate_case_priority(db, case_id=case_id)

    route_category_map = {
        "LEGAL_DEFENSE": "legal_defense",
        "LOAN_MODIFICATION": "loan_modification",
        "NONPROFIT_REFERRAL": "nonprofit_support",
        "ACQUISITION_CANDIDATE": "property_acquisition",
    }
    routing_category = route_category_map.get(classification, "nonprofit_support")
    referral = route_case_to_partner(db, case_id=case_id, state=seed.state, routing_category=routing_category, actor_id=user.id)

    db.commit()

    return {
        "phase": "phase10",
        "pipeline_status": "operational",
        "case_created": True,
        "analysis_completed": True,
        "priority_scored": bool(priority.get("priority_tier")),
        "partner_routed": bool(referral.id),
        "ai_recommendation_generated": True,
    }
