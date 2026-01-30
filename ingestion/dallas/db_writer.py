from uuid import uuid4

from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.cases import Case
from models.enums import CaseStatus
from models.properties import Property


def _get_or_create_property(session: Session, record: dict) -> Property:
    existing = (
        session.query(Property)
        .filter(Property.external_id == record["external_id"])
        .first()
    )
    if existing:
        return existing

    prop = Property(
        external_id=record["external_id"],
        address=record["address"],
        city=record["city"],
        state=record["state"],
        zip=record["zip"],
        county=record.get("county"),
        mortgagor=record.get("mortgagor"),
        mortgagee=record.get("mortgagee"),
        trustee=record.get("trustee"),
        auction_date=record.get("auction_date"),
        source=record.get("source"),
    )
    session.add(prop)
    session.flush()
    return prop


def write_to_db(record: dict) -> None:
    session = SessionLocal()
    try:
        prop = _get_or_create_property(session, record)
        case = Case(
            id=uuid4(),
            status=CaseStatus[record["status"]],
            created_by=uuid4(),
            program_type="FORECLOSURE_PREVENTION",
            property_id=prop.id,
        )
        session.add(case)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
