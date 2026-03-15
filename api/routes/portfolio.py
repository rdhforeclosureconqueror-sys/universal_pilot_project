from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from db.session import get_db
from app.services.property_portfolio_service import add_property_to_portfolio, calculate_portfolio_equity


router = APIRouter(prefix="/portfolio", tags=["Property Portfolio"])


class AddPropertyRequest(BaseModel):
    case_id: UUID | None = None
    property_address: str
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    acquisition_cost: float | None = None
    estimated_value: float | None = None
    loan_amount: float | None = None
    tenant_homeowner_id: UUID | None = None
    lease_terms: str | None = None
    equity_share_percentage: float | None = None
    portfolio_status: str | None = "active"


@router.post("/add-property")
def add_property(
    request: AddPropertyRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if request.case_id:
        PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="portfolio.add_property")

    asset = add_property_to_portfolio(db, payload=request.model_dump(), actor_id=user.id)
    db.commit()

    return {"property_asset_id": str(asset.id), "portfolio_status": asset.portfolio_status}


@router.get("/summary")
def portfolio_summary(
    case_id: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if case_id:
        PolicyAuthorizer(db).require_case_action(user=user, case_id=case_id, action="portfolio.summary")
    else:
        # require at least one scoped case for policy compatibility
        raise HTTPException(status_code=400, detail="case_id query parameter is required")
    return calculate_portfolio_equity(db)
