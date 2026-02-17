import logging
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from sqlalchemy.orm import Session

from models.cases import Case
from models.enums import CaseStatus
from models.properties import Property
from models.deal_scores import DealScore
from models.leads import Lead
from models.audit_logs import AuditLog
from services.workflow_engine import initialize_case_workflow, sync_case_workflow

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# PROPERTY
# ---------------------------------------------------------

def _get_or_create_property(session: Session, record: dict) -> Property:
    external_id = record.get("external_id")

    if external_id:
        existing = (
            session.query(Property)
            .filter(Property.external_id == external_id)
            .first()
        )
        if existing:
            return existing

    prop = Property(
        external_id=external_id or str(uuid4()),
        address=(record.get("address") or "").strip(),
        city=(record.get("city") or "Dallas").strip(),
        state=(record.get("state") or "TX").strip(),
        zip=(record.get("zip") or "").strip(),
        county=(record.get("county") or "Dallas").strip(),
        mortgagor=(record.get("mortgagor") or "").strip(),
        mortgagee=(record.get("mortgagee") or "").strip(),
        trustee=(record.get("trustee") or "").strip(),
        auction_date=record.get("auction_date"),
        source=(record.get("source") or "unknown").strip(),
    )

    session.add(prop)
    session.flush()
    return prop


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def _parse_opening_bid(value) -> Optional[float]:
    if value in (None, ""):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    cleaned = str(value).replace("$", "").replace(",", "").strip()

    try:
        return float(cleaned)
    except Exception:
        return None


def _safe_case_status(value: Optional[str]) -> CaseStatus:
    if not value:
        return CaseStatus.PRE_FORECLOSURE

    try:
        return CaseStatus(value)
    except Exception:
        logger.warning(
            "Invalid CaseStatus '%s' — defaulting to PRE_FORECLOSURE",
            value,
        )
        return CaseStatus.PRE_FORECLOSURE


def _calculate_score(auction_date: Optional[datetime]) -> tuple[int, str, str, Optional[int]]:
    urgency_days = None

    if auction_date:
        try:
            if auction_date.tzinfo is None:
                auction_date = auction_date.replace(tzinfo=timezone.utc)

            urgency_days = (auction_date - datetime.now(timezone.utc)).days
        except Exception as e:
            logger.warning("Auction date calculation failed: %s", e)

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

    return score, tier, exit_strategy, urgency_days


# ---------------------------------------------------------
# LEAD UPSERT
# ---------------------------------------------------------

def _get_or_create_lead(
    session: Session,
    record: dict,
    score: int,
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


# ---------------------------------------------------------
# MAIN WRITER
# ---------------------------------------------------------

def write_to_db(record: dict, session: Session) -> None:
    try:
        prop = _get_or_create_property(session, record)

        canonical_fields = {
            "external_id", "address", "city", "state", "zip", "county",
            "trustee", "mortgagor", "mortgagee", "auction_date", "source",
            "status", "opening_bid", "case_number",
            "assessed_value", "est_balance",
        }

        extra_fields = {
            k: v for k, v in record.items()
            if k not in canonical_fields
        }

        # Prevent duplicate case for same property + auction date
        existing_case = (
            session.query(Case)
            .filter(
                Case.property_id == prop.id,
            )
            .first()
        )

        if existing_case:
            logger.info("Case already exists for property %s — skipping.", prop.id)
            return

        case = Case(
            id=uuid4(),
            status=_safe_case_status(record.get("status")),
            created_by=uuid4(),
            program_type="FORECLOSURE_PREVENTION",
            program_key="FORECLOSURE_PREVENTION",
            meta={"extra_fields": extra_fields} if extra_fields else {},
            property_id=prop.id,
        )

        session.add(case)
        session.flush()

        score, tier, exit_strategy, urgency_days = _calculate_score(
            prop.auction_date
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
        lead = _get_or_create_lead(
            session=session,
            record=record,
            score=score,
            tier=tier,
            exit_strategy=exit_strategy,
        )

        session.add_all([
            AuditLog(
                id=uuid4(),
                case_id=case.id,
                actor_id=None,
                actor_is_ai=True,
                action_type="auction_import_created",
                reason_code="system_ingest",
                before_json=None,
                after_json={"source": record.get("source")},
            ),
            AuditLog(
                id=uuid4(),
                case_id=case.id,
                actor_id=None,
                actor_is_ai=True,
                action_type="lead_created",
                reason_code="system_ingest",
                before_json=None,
                after_json={"lead_id": lead.lead_id},
            ),
            AuditLog(
                id=uuid4(),
                case_id=case.id,
                actor_id=None,
                actor_is_ai=True,
                action_type="case_created",
                reason_code="system_ingest",
                before_json=None,
                after_json={"status": case.status.value if hasattr(case.status, "value") else str(case.status)},
            ),
        ])

        initialize_case_workflow(session, case.id)
        sync_case_workflow(session, case.id)

        _get_or_create_lead(
            session=session,
            record=record,
            score=score,
            tier=tier,
            exit_strategy=exit_strategy,
        )

        logger.info(
            "Inserted case + deal_score for property %s (case_number=%s)",
            prop.id,
            record.get("case_number"),
        )

    except Exception as e:
        logger.exception("Failed to write record to DB")
        raise
