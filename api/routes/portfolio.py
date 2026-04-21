from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from db.session import get_db
from app.models.cases import Case
from app.models.housing_intelligence import ForeclosureCaseData, PropertyAsset
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
        raise HTTPException(status_code=400, detail="case_id query parameter is required")
    return calculate_portfolio_equity(db)


@router.get("/workspace/assets")
def get_portfolio_workspace_assets(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    rows = (
        db.query(PropertyAsset, ForeclosureCaseData)
        .outerjoin(ForeclosureCaseData, ForeclosureCaseData.case_id == PropertyAsset.case_id)
        .order_by(PropertyAsset.created_at.desc())
        .limit(300)
        .all()
    )

    return [
        {
            "property_asset_id": str(asset.id),
            "case_id": str(asset.case_id) if asset.case_id else None,
            "property_address": asset.property_address,
            "city": asset.city,
            "state": asset.state,
            "portfolio_status": asset.portfolio_status,
            "estimated_value": asset.estimated_value,
            "loan_amount": asset.loan_amount,
            "equity_estimate": round(float(asset.estimated_value or 0) - float(asset.loan_amount or 0), 2),
            "foreclosure_stage": profile.foreclosure_stage if profile else None,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
        }
        for asset, profile in rows
    ]


@router.get("/workspace/assets/{property_asset_id}")
def get_portfolio_workspace_asset_detail(
    property_asset_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    asset = db.query(PropertyAsset).filter(PropertyAsset.id == property_asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Portfolio asset not found")

    case = db.query(Case).filter(Case.id == asset.case_id).first() if asset.case_id else None
    profile = db.query(ForeclosureCaseData).filter(ForeclosureCaseData.case_id == asset.case_id).first() if asset.case_id else None

    summary = calculate_portfolio_equity(db)

    return {
        "asset": {
            "property_asset_id": str(asset.id),
            "case_id": str(asset.case_id) if asset.case_id else None,
            "property_address": asset.property_address,
            "city": asset.city,
            "state": asset.state,
            "zip_code": asset.zip_code,
            "acquisition_cost": asset.acquisition_cost,
            "estimated_value": asset.estimated_value,
            "loan_amount": asset.loan_amount,
            "equity_share_percentage": asset.equity_share_percentage,
            "portfolio_status": asset.portfolio_status,
            "lease_terms": asset.lease_terms,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
            "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
        },
        "case_context": {
            "case_status": case.status.value if case and case.status else None,
            "foreclosure_stage": profile.foreclosure_stage if profile else None,
            "arrears_amount": profile.arrears_amount if profile else None,
            "estimated_property_value": profile.estimated_property_value if profile else None,
            "loan_balance": profile.loan_balance if profile else None,
        },
        "summary": summary,
    }


@router.get("/workspace/summary")
def portfolio_workspace_summary(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    summary = calculate_portfolio_equity(db)
    active_count = db.query(PropertyAsset).filter(PropertyAsset.portfolio_status == "active").count()
    watchlist_count = db.query(PropertyAsset).filter(PropertyAsset.portfolio_status == "watchlist").count()
    return {
        **summary,
        "active_assets": active_count,
        "watchlist_assets": watchlist_count,
    }
