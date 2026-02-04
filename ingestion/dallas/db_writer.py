import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from models.cases import Case
from models.enums import CaseStatus
from models.properties import Property
from models.deal_scores import DealScore
from models.leads import Lead

logger = logging.getLogger(__name__)


def _get_or_create_property(session: Session, record: dict) -> Property:
    existing = (
        session.query(Property)
        .filter(Property.external_id == record.get("external_id"))
        .first()
    )
    if existing:
        return existing

    prop = Property(
        external_id=record.get("external_id") or str(uuid4()),
        address=record.get("address", "").strip(),
        city=record.get("city", "Dallas").strip(),
        state=record.get("state", "TX").strip(),
        zip=record.get("zip", "").strip(),
        county=record.get("county", "Dallas").strip(),
        mortgagor=record.get("mortgagor", "").strip(),
        mortgagee=record.get("mortgagee", "").strip(),
        trustee=record.get("trustee", "").strip(),
        auction_date=record.get("auction_date"),
        source=record.get("source", "unknown").strip(),
    )

    session.add(prop)
    session.flush()
    return prop


def _parse_opening_bid(value) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _get_or_create_lead(
    session: Session,
    record: dict,
    score: float,
    tier: str,
    exit_strategy: str,
) -> Lead:
    lead_id = (
        record.get("external_id")
        or record.get("case_number")
        or f"lead-{uuid4().hex[:12]}"
    )
    lead = session.query(Lead).filter(Lead.lead_id == lead_id).first()
    lead_data = {
        "lead_id": lead_id,
        "source": record.get("source"),
        "address": record.get("address", "").strip(),
        "city": record.get("city", "Dallas").strip(),
        "state": record.get("state", "TX").strip(),
        "zip": record.get("zip", "").strip(),
        "county": record.get("county", "Dallas").strip(),
        "trustee": record.get("trustee", "").strip(),
        "mortgagor": record.get("mortgagor", "").strip(),
        "mortgagee": record.get("mortgagee", "").strip(),
        "auction_date": record.get("auction_date"),
        "case_number": record.get("case_number"),
        "opening_bid": _parse_opening_bid(record.get("opening_bid")),
        "status": record.get("status"),
        "score": score,
        "tier": tier,
        "exit_strategy": exit_strategy,
    }

    if lead:
        for key, value in lead_data.items():
            setattr(lead, key, value)
    else:
        lead = Lead(**lead_data)
        session.add(lead)

    session.flush()
    return lead


def write_to_db(record: dict, session: Session) -> None:
    try:
        prop = _get_or_create_property(session, record)

        case = Case(
            id=uuid4(),
            status=CaseStatus.get(record.get("status", "PRE_FORECLOSURE")),
            created_by=uuid4(),
            program_type="FORECLOSURE_PREVENTION",
            property_id=prop.id,
        )

        session.add(case)
        session.flush()

        urgency_days = None
        if prop.auction_date:
            try:
                urgency_days = (
                    prop.auction_date.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
                ).days
            except Exception as e:
                logger.warning(f"Invalid auction_date format: {e}")

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

        exit_strategy = (
            "AUCTION_RUSH"
            if urgency_days is not None and urgency_days <= 7
            else "NEGOTIATE"
        )

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
        _get_or_create_lead(
            session=session,
            record=record,
            score=score,
            tier=tier,
            exit_strategy=exit_strategy,
        )

        logger.info(
            "✅ Inserted case for property %s (case_number=%s)",
            prop.id,
            record.get("case_number"),
        )

    except Exception as e:
        logger.error("❌ Failed to write record to DB: %s", e)
        raise
