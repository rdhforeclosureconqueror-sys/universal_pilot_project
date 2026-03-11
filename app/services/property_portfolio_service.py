from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.housing_intelligence import PropertyAsset


def add_property_to_portfolio(db: Session, *, payload: dict, actor_id: UUID | None) -> PropertyAsset:
    asset = PropertyAsset(**payload)
    db.add(asset)
    db.flush()

    db.add(
        AuditLog(
            id=uuid4(),
            case_id=asset.case_id,
            actor_id=actor_id,
            actor_is_ai=False,
            action_type="property_asset_added",
            reason_code="portfolio_add_property",
            before_state={},
            after_state={"property_asset_id": str(asset.id), "property_address": asset.property_address},
            policy_version_id=None,
        )
    )
    return asset


def update_property_value(db: Session, *, property_asset_id: UUID, estimated_value: float, actor_id: UUID | None) -> PropertyAsset | None:
    asset = db.query(PropertyAsset).filter(PropertyAsset.id == property_asset_id).first()
    if not asset:
        return None
    before = asset.estimated_value
    asset.estimated_value = estimated_value
    db.flush()

    db.add(
        AuditLog(
            id=uuid4(),
            case_id=asset.case_id,
            actor_id=actor_id,
            actor_is_ai=False,
            action_type="property_value_updated",
            reason_code="portfolio_update_value",
            before_state={"estimated_value": before},
            after_state={"estimated_value": estimated_value},
            policy_version_id=None,
        )
    )
    return asset


def calculate_portfolio_equity(db: Session) -> dict:
    assets = db.query(PropertyAsset).all()
    total_assets = len(assets)
    portfolio_value = sum(float(a.estimated_value or 0) for a in assets)
    portfolio_loans = sum(float(a.loan_amount or 0) for a in assets)
    portfolio_equity = portfolio_value - portfolio_loans

    return {
        "total_assets": total_assets,
        "portfolio_value": round(portfolio_value, 2),
        "portfolio_loans": round(portfolio_loans, 2),
        "portfolio_equity": round(portfolio_equity, 2),
    }
