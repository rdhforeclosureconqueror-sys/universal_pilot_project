from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from db.session import get_db
from app.services.foreclosure_intelligence_service import create_foreclosure_profile
from app.services.property_analysis_service import (
    calculate_acquisition_score,
    calculate_equity,
    calculate_ltv,
    calculate_rescue_score,
    classify_intervention,
)


router = APIRouter(prefix="/foreclosure", tags=["Foreclosure Intelligence"])


class ForeclosureCreateProfileRequest(BaseModel):
    case_id: UUID
    property_address: str
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    loan_balance: float | None = None
    estimated_property_value: float | None = None
    monthly_payment: float | None = None
    arrears_amount: float | None = None
    foreclosure_stage: str | None = None
    auction_date: str | None = None
    lender_name: str | None = None
    servicer_name: str | None = None
    occupancy_status: str | None = None
    homeowner_income: float | None = None
    homeowner_hardship_reason: str | None = None


class PropertyAnalysisRequest(BaseModel):
    case_id: UUID
    estimated_property_value: float
    loan_balance: float
    arrears_amount: float = 0
    homeowner_income: float = 0
    foreclosure_stage: str = "pre_foreclosure"


@router.post("/create-profile")
def create_profile(
    request: ForeclosureCreateProfileRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="foreclosure.profile.create")

    payload = request.model_dump(exclude={"case_id"})
    profile = create_foreclosure_profile(db, case_id=request.case_id, payload=payload, actor_id=user.id)
    db.commit()

    return {"profile_id": str(profile.id), "case_id": str(profile.case_id), "foreclosure_stage": profile.foreclosure_stage}


@router.post("/analyze-property")
def analyze_property(
    request: PropertyAnalysisRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="foreclosure.property.analyze")

    equity = calculate_equity(estimated_property_value=request.estimated_property_value, loan_balance=request.loan_balance)
    ltv = calculate_ltv(loan_balance=request.loan_balance, estimated_property_value=request.estimated_property_value)
    rescue_score = calculate_rescue_score(
        arrears_amount=request.arrears_amount,
        homeowner_income=request.homeowner_income,
        foreclosure_stage=request.foreclosure_stage,
    )
    acquisition_score = calculate_acquisition_score(equity=equity, ltv=ltv, foreclosure_stage=request.foreclosure_stage)
    classification = classify_intervention(rescue_score=rescue_score, acquisition_score=acquisition_score, ltv=ltv)

    return {
        "case_id": str(request.case_id),
        "equity": equity,
        "ltv": ltv,
        "rescue_score": rescue_score,
        "acquisition_score": acquisition_score,
        "classification": classification,
    }
