from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from db.session import get_db
from app.models.deal_scores import DealScore
from app.models.properties import Property
from app.models.cases import Case

router = APIRouter(prefix="/deals", tags=["Deals"])

@router.get("/top")
def top_deals(limit: int = 25, db: Session = Depends(get_db)):
    """
    Returns the top deals based on DealScore, joined with related Property and Case data.
    Sorted descending by score. Optional `limit` parameter.
    """

    try:
        rows = (
            db.query(DealScore, Property, Case)
            .join(Property, DealScore.property_id == Property.id)
            .join(Case, DealScore.case_id == Case.id)
            .order_by(DealScore.score.desc())
            .limit(limit)
            .all()
        )

        if not rows:
            return {"message": "No top deals found."}

        results = []
        for score, prop, case in rows:
            results.append({
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
                "case_status": (
                    case.status.value if hasattr(case.status, "value") else str(case.status)
                ),
            })

        return results

    except SQLAlchemyError as e:
        print("❌ Database error in /deals/top:", str(e))
        raise HTTPException(status_code=500, detail="Database query failed.")

    except Exception as e:
        print("❌ Unexpected error in /deals/top:", str(e))
        raise HTTPException(status_code=500, detail="Internal server error.")
