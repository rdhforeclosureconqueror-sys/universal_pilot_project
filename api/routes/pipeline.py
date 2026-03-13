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


router = APIRouter(prefix="/pipeline", tags=["Foreclosure Pipeline"])


@router.post("/foreclosure-analysis")
def foreclosure_analysis_pipeline(
    request: ForeclosureCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # 1-2 create case/profile
    create_result = create_foreclosure_profile(
        db,
        case_id=request.case_id,
        payload=request.model_dump(exclude={"case_id"}, exclude_none=True),
        actor_id=user.id,
    )
    case_id = create_result["case_id"]

    # 3 analyze property
    equity = calculate_equity(estimated_property_value=request.estimated_property_value, loan_balance=request.loan_balance)
    ltv = calculate_ltv(loan_balance=request.loan_balance, estimated_property_value=request.estimated_property_value)
    rescue_score = calculate_rescue_score(
        arrears_amount=request.arrears_amount,
        homeowner_income=request.homeowner_income or 0,
        foreclosure_stage=request.foreclosure_stage,
    )
    acquisition_score = calculate_acquisition_score(equity=equity, ltv=ltv, foreclosure_stage=request.foreclosure_stage)
    classification = classify_intervention(rescue_score=rescue_score, acquisition_score=acquisition_score, ltv=ltv)

    # 4 priority
    priority = calculate_case_priority(db, case_id=case_id)

    # 5 route partner
    route_category_map = {
        "LEGAL_DEFENSE": "legal_defense",
        "LOAN_MODIFICATION": "loan_modification",
        "NONPROFIT_REFERRAL": "nonprofit_support",
        "ACQUISITION_CANDIDATE": "property_acquisition",
    }
    routing_category = route_category_map.get(classification, "nonprofit_support")
    referral = route_case_to_partner(
        db,
        case_id=case_id,
        state=request.state,
        routing_category=routing_category,
        actor_id=user.id,
    )

    # 6 AI-style recommendation (deterministic placeholder)
    recommended_action = {
        "LEGAL_DEFENSE": "Immediate legal defense intake",
        "LOAN_MODIFICATION": "Prepare loan modification package",
        "NONPROFIT_REFERRAL": "Route to nonprofit stabilization support",
        "ACQUISITION_CANDIDATE": "Evaluate mission-aligned acquisition",
    }.get(classification, "Route to housing support")

    db.commit()

    return {
        "case_id": str(case_id),
        "equity": equity,
        "ltv": ltv,
        "priority_tier": priority["priority_tier"],
        "recommended_action": recommended_action,
        "partner_route": referral.routing_category,
    }
