import logging
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from sqlalchemy.orm import Session

from models.audit_logs import AuditLog
from models.cases import Case
from models.deal_scores import DealScore
from models.enums import CaseStatus
from models.leads import Lead
from models.properties import Property
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
    except Exception:
        return None


def _safe_case_status(value: str | None) -> CaseStatus:
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


def _calculate_score(
    auction_date: datetime | None,
) -> tuple[int, str, str, int | None]:
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

def _case_status_from_record(raw_status) -> CaseStatus:
    if raw_status is None:
        return CaseStatus.PRE_FORECLOSURE

    token = str(raw_status).strip()
    if not token:
        return CaseStatus.PRE_FORECLOSURE

    try:
        return CaseStatus(token)
    except Exception:
        return CaseStatus.PRE_FORECLOSURE


def _case_canonical_key(prop: Property, auction_date, record: dict) -> str:
    date_token = auction_date.isoformat() if auction_date else "unknown"
    source = record.get("source", "unknown")
    return f"{prop.external_id}|{date_token}|{source}"


def _get_or_create_case(session: Session, prop: Property, record: dict):
    auction_date = record.get("auction_date")
    canonical_key = _case_canonical_key(prop, auction_date, record)

    existing = (
        session.query(Case)
        .filter(Case.canonical_key == canonical_key)
        .first()
    )

    if existing:
        session.add(
            AuditLog(
                id=uuid4(),
                case_id=existing.id,
                actor_id=None,
                actor_is_ai=True,
                action_type="ingestion_duplicate_detected",
                reason_code="idempotent_replay",
                before_json=None,
                after_json={"canonical_key": canonical_key},
            )
        )
        return existing, False

    # Canonical vs extra metadata split
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

    case = Case(
        id=uuid4(),
        status=_case_status_from_record(record.get("status")),
        created_by=uuid4(),
        program_type="FORECLOSURE_PREVENTION",
        program_key="foreclosure_stabilization_v1",
        property_id=prop.id,
        auction_date=auction_date,
        canonical_key=canonical_key,
        meta={
            "source": record.get("source"),
            "case_number": record.get("case_number"),
            **extra_fields,
        },
    )

        session.add(case)
    session.flush()

    session.add(
        AuditLog(
            id=uuid4(),
            case_id=case.id,
            actor_id=None,
            actor_is_ai=True,
            action_type="case_created_from_ingestion",
            reason_code="auction_import",
            before_json=None,
            after_json={
                "canonical_key": canonical_key,
                "extra_fields": extra_fields if extra_fields else {},
            },
        )
    )

    return case, True



def _get_or_create_deal_score(
    session: Session,
    case: Case,
    prop: Property,
    score: int,
    tier: str,
    exit_strategy: str,
    urgency_days: int | None,
):
    ds = (
        session.query(DealScore)
        .filter(DealScore.case_id == case.id)
        .first()
    )

    if ds:
        ds.score = score
        ds.tier = tier
        ds.exit_strategy = exit_strategy
        ds.urgency_days = urgency_days
    else:
        ds = DealScore(
            id=uuid4(),

            case_id=case.id,
            property_id=prop.id,

            score=score,
            tier=tier,
            exit_strategy=exit_strategy,
            urgency_days=urgency_days,
        )
        session.add(ds)

    session.flush()
    return ds

def write_to_db(record: dict, session: Session) -> None:
    try:
        prop = _get_or_create_property(session, record)

        score, tier, exit_strategy, urgency_days = _calculate_score(
            prop.auction_date
        )

        case, created_case = _get_or_create_case(session, prop, record)
        _get_or_create_deal_score(
            session=session,
            case=case,
            prop=prop,
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

        if created_case:
            session.add_all([
                AuditLog(
                    id=uuid4(),
                    case_id=case.id, )
            },
        )
    )

    session.add(
        AuditLog(
            id=uuid4(),
            case_id=case.id,
            actor_id=None,
            actor_is_ai=True,
            action_type="auction_import_created",
            reason_code="system_ingest",
            before_json=None,
            after_json={"source": record.get("source")},
        )
    )

if created_lead:
    session.add(
        AuditLog(
            id=uuid4(),
            case_id=case.id,
            actor_id=None,
            actor_is_ai=True,
            action_type="lead_created",
            reason_code="system_ingest",
            before_json=None,
            after_json={"lead_id": lead.lead_id},
        )
    )

# Initialize + sync workflow only when case is new
if created_case:
    initialize_case_workflow(session, case.id)
    sync_case_workflow(session, case.id)

logger.info(
    "✅ Upserted foreclosure entities for property %s (case_number=%s)",
    prop.id,
    record.get("case_number"),
)

    except Exception as e:
        logger.exception("Failed to write record to DB")
        raise
