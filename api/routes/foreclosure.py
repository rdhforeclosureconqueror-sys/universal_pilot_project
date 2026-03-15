from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.foreclosure_intelligence import ForeclosureAnalyzeRequest, ForeclosureCreateRequest
from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from db.session import get_db
from app.services.foreclosure_intelligence_service import calculate_case_priority, create_foreclosure_profile
from app.services.property_analysis_service import (
    calculate_acquisition_score,
    calculate_equity,
    calculate_ltv,
    calculate_rescue_score,
    classify_intervention,
)


router = APIRouter(prefix="/foreclosure", tags=["Foreclosure Intelligence"])


@router.post("/create-profile")
def create_profile(
    request: ForeclosureCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if request.case_id:
        PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="foreclosure.profile.create")

    payload = request.model_dump(exclude={"case_id"}, exclude_none=True)
    result = create_foreclosure_profile(db, case_id=request.case_id, payload=payload, actor_id=user.id)
    db.commit()

    return {
        "case_id": str(result["case_id"]),
        "profile_created": bool(result["profile_created"]),
    }


@router.post("/analyze-property")
def analyze_property(
    request: ForeclosureAnalyzeRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="foreclosure.property.analyze")

    equity = calculate_equity(estimated_property_value=request.estimated_property_value, loan_balance=request.loan_balance)
    ltv = calculate_ltv(loan_balance=request.loan_balance, estimated_property_value=request.estimated_property_value)
    rescue_score = calculate_rescue_score(
        arrears_amount=request.arrears_amount,
        homeowner_income=request.homeowner_income or 0,
        foreclosure_stage=request.foreclosure_stage,
    )
    acquisition_score = calculate_acquisition_score(equity=equity, ltv=ltv, foreclosure_stage=request.foreclosure_stage)
    classification = classify_intervention(rescue_score=rescue_score, acquisition_score=acquisition_score, ltv=ltv)
    priority = calculate_case_priority(db, case_id=request.case_id)

    return {
        "case_id": str(request.case_id),
        "equity": equity,
        "ltv": ltv,
        "rescue_score": rescue_score,
        "acquisition_score": acquisition_score,
        "classification": classification,
        "priority": priority,
    }
