from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from app.models.properties import Property
from app.models.cases import Case

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.get("/")
def list_properties(db: Session = Depends(get_db)):
    properties = db.query(Property).all()
    return [
        {
            "id": str(prop.id),
            "external_id": prop.external_id,
            "address": prop.address,
            "city": prop.city,
            "state": prop.state,
            "zip": prop.zip,
            "county": prop.county,
            "property_type": prop.property_type,
            "year_built": prop.year_built,
            "sqft": prop.sqft,
            "beds": prop.beds,
            "baths": prop.baths,
            "assessed_value": prop.assessed_value,
            "mortgagor": prop.mortgagor,
            "mortgagee": prop.mortgagee,
            "trustee": prop.trustee,
            "loan_type": prop.loan_type,
            "interest_rate": prop.interest_rate,
            "orig_loan_amount": prop.orig_loan_amount,
            "est_balance": prop.est_balance,
            "auction_date": prop.auction_date.isoformat() if prop.auction_date else None,
            "auction_time": prop.auction_time,
            "source": prop.source,
            "latitude": prop.latitude,
            "longitude": prop.longitude,
        }
        for prop in properties
    ]


@router.get("/map")
def map_properties(db: Session = Depends(get_db)):
    properties = db.query(Property).all()
    case_lookup = {
        str(case.property_id): case
        for case in db.query(Case).filter(Case.property_id.isnot(None)).all()
    }
    results = []
    for prop in properties:
        case = case_lookup.get(str(prop.id))
        results.append(
            {
                "id": str(prop.id),
                "address": prop.address,
                "latitude": prop.latitude,
                "longitude": prop.longitude,
                "case_status": case.status.value if case else None,
                "case_id": str(case.id) if case else None,
            }
        )
    return results


@router.get("/{property_id}")
def get_property(property_id: str, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        return {"detail": "Property not found"}
    case = db.query(Case).filter(Case.property_id == prop.id).first()
    return {
        "id": str(prop.id),
        "external_id": prop.external_id,
        "address": prop.address,
        "city": prop.city,
        "state": prop.state,
        "zip": prop.zip,
        "county": prop.county,
        "property_type": prop.property_type,
        "year_built": prop.year_built,
        "sqft": prop.sqft,
        "beds": prop.beds,
        "baths": prop.baths,
        "assessed_value": prop.assessed_value,
        "mortgagor": prop.mortgagor,
        "mortgagee": prop.mortgagee,
        "trustee": prop.trustee,
        "loan_type": prop.loan_type,
        "interest_rate": prop.interest_rate,
        "orig_loan_amount": prop.orig_loan_amount,
        "est_balance": prop.est_balance,
        "auction_date": prop.auction_date.isoformat() if prop.auction_date else None,
        "auction_time": prop.auction_time,
        "source": prop.source,
        "latitude": prop.latitude,
        "longitude": prop.longitude,
        "case_id": str(case.id) if case else None,
        "case_status": case.status.value if case else None,
    }
