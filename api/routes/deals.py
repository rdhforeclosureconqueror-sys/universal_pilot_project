from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from models.deal_scores import DealScore
from models.properties import Property
from models.cases import Case

router = APIRouter(prefix="/deals", tags=["Deals"])


@router.get("/top")
def top_deals(limit: int = 25, db: Session = Depends(get_db)):
    rows = (
        db.query(DealScore, Property, Case)
        .join(Property, DealScore.property_id == Property.id)
        .join(Case, DealScore.case_id == Case.id)
        .order_by(DealScore.score.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "deal_id": str(score.id),
            "score": score.score,
            "tier": score.tier,
            "exit_strategy": score.exit_strategy,
            "urgency_days": score.urgency_days,
            "property_id": str(prop.id),
            "case_id": str(case.id),
            "address": prop.address,
            "city": prop.city,
            "state": prop.state,
            "zip": prop.zip,
            "auction_date": prop.auction_date.isoformat() if prop.auction_date else None,
            "case_status": case.status.value,
        }
        for score, prop, case in rows
    ]
