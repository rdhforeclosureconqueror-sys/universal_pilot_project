import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from models.cases import Case
from models.enums import CaseStatus
from models.properties import Property
from models.deal_scores import DealScore

logger = logging.getLogger(__name__)


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


def write_to_db(record: dict, session: Session) -> None:
    prop = _get_or_create_property(session, record)
    case = Case(
        id=uuid4(),
        status=CaseStatus[record["status"]],
        created_by=uuid4(),
        program_type="FORECLOSURE_PREVENTION",
        property_id=prop.id,
    )
    session.add(case)
    session.flush()
    urgency_days = None
    if prop.auction_date:
        urgency_days = (prop.auction_date.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days
    score = 50
    if urgency_days is not None:
        if urgency_days <= 7:
            score += 20
        elif urgency_days <= 30:
            score += 10
        elif urgency_days <= 90:
            score += 5
    score = max(0, min(100, score))
    if score >= 80:
        tier = "A"
    elif score >= 60:
        tier = "B"
    else:
        tier = "C"
    exit_strategy = "AUCTION_RUSH" if urgency_days is not None and urgency_days <= 7 else "NEGOTIATE"
    deal_score = DealScore(
        id=uuid4(),
        property_id=prop.id,
        case_id=case.id,
        score=score,
        tier=tier,
        exit_strategy=exit_strategy,
        urgency_days=urgency_days,
    )
    session.add(deal_score)
    logger.info(
        "Inserted case for property %s (%s)",
        prop.id,
        record.get("case_number"),
    )
