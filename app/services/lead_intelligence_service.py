from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.cases import Case
from app.models.enums import CaseStatus
from app.models.lead_intelligence import LeadScore, LeadSource, PropertyLead
from app.models.policy_versions import PolicyVersion


SCORE_THRESHOLD = 65.0


def ingest_leads(db: Session, *, source_name: str, source_type: str, leads: list[dict]) -> dict:
    source = db.query(LeadSource).filter(LeadSource.source_name == source_name).first()

    if not source:
        source = LeadSource(source_name=source_name, source_type=source_type)
        db.add(source)
        db.flush()

    ingested = 0

    for lead in leads:
        if deduplicate_leads(
            db,
            source_id=source.id,
            property_address=lead.get("property_address", ""),
        ):
            continue

        db.add(
            PropertyLead(
                source_id=source.id,
                property_address=lead.get("property_address", ""),
                city=lead.get("city"),
                state=lead.get("state"),
                zip_code=lead.get("zip_code"),
                foreclosure_stage=lead.get("foreclosure_stage"),
                tax_delinquent=str(bool(lead.get("tax_delinquent", False))).lower(),
                equity_estimate=float(lead.get("equity_estimate", 0) or 0),
                auction_date=lead.get("auction_date"),
                owner_occupancy=str(bool(lead.get("owner_occupancy", True))).lower(),
                raw_payload=lead,
            )
        )

        ingested += 1

    db.flush()

    return {
        "source": source_name,
        "leads_ingested": ingested,
    }


def deduplicate_leads(db: Session, *, source_id: UUID, property_address: str) -> bool:
    existing = (
        db.query(PropertyLead)
        .filter(
            PropertyLead.source_id == source_id,
            PropertyLead.property_address == property_address,
        )
        .first()
    )

    return existing is not None


def score_property_lead(db: Session, *, lead_id: UUID, actor_id: UUID | None = None) -> dict:
    lead = db.query(PropertyLead).filter(PropertyLead.id == lead_id).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    score = 0.0
    stage = (lead.foreclosure_stage or "").lower()

    if "auction" in stage:
        score += 30
    elif "default" in stage:
        score += 20
    elif "pre" in stage:
        score += 15

    if str(lead.tax_delinquent).lower() == "true":
        score += 20

    if float(lead.equity_estimate or 0) > 50000:
        score += 20

    if lead.auction_date:
        days = (lead.auction_date - datetime.now(timezone.utc)).days
        if days <= 45:
            score += 15

    if str(lead.owner_occupancy).lower() == "true":
        score += 10

    score = round(min(100.0, score), 2)

    grade = "A" if score >= 80 else "B" if score >= 65 else "C"

    score_row = LeadScore(
        lead_id=lead.id,
        score=score,
        grade=grade,
        recommended_action="create_case" if score >= SCORE_THRESHOLD else "monitor",
    )

    db.add(score_row)
    db.flush()

    created_case_id = None

    if score >= SCORE_THRESHOLD and actor_id:
        created_case_id = create_case_from_lead(
            db,
            lead_id=lead.id,
            actor_id=actor_id,
        )
        score_row.created_case_id = created_case_id
        db.flush()

    return {
        "lead_id": str(lead.id),
        "score": score,
        "grade": grade,
        "created_case_id": str(created_case_id) if created_case_id else None,
    }


def create_case_from_lead(db: Session, *, lead_id: UUID, actor_id: UUID) -> UUID:
    lead = db.query(PropertyLead).filter(PropertyLead.id == lead_id).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    policy = (
        db.query(PolicyVersion)
        .filter(PolicyVersion.is_active.is_(True))
        .order_by(PolicyVersion.created_at.desc())
        .first()
    )

    if not policy:
        raise HTTPException(status_code=400, detail="No active policy for lead conversion")

    case = Case(
        status=CaseStatus.intake_submitted,
        created_by=actor_id,
        program_type=policy.program_key,
        program_key=policy.program_key,
        case_type="lead_intelligence",
        meta={
            "property_address": lead.property_address,
            "city": lead.city,
            "state": lead.state,
            "lead_id": str(lead.id),
        },
        policy_version_id=policy.id,
    )

    db.add(case)
    db.flush()

    return case.id


def weekly_foreclosure_scan(db: Session) -> dict:
    connectors = [
        dallas_county_foreclosure_connector,
        tarrant_county_trustee_connector,
        collin_county_notice_connector,
    ]

    total = 0

    for connector in connectors:
        result = connector(db)
        total += result.get("leads_ingested", 0)

    return {
        "status": "success",
        "weekly_leads_ingested": total,
    }


def dallas_county_foreclosure_connector(db: Session) -> dict:
    leads = [
        {
            "property_address": "100 Elm St",
            "city": "Dallas",
            "state": "TX",
            "foreclosure_stage": "pre_foreclosure",
            "tax_delinquent": True,
            "equity_estimate": 60000,
        }
    ]

    return ingest_leads(
        db,
        source_name="dallas_county_foreclosure_connector",
        source_type="foreclosure_filings",
        leads=leads,
    )


def tarrant_county_trustee_connector(db: Session) -> dict:
    leads = [
        {
            "property_address": "200 Oak St",
            "city": "Fort Worth",
            "state": "TX",
            "foreclosure_stage": "auction_scheduled",
            "tax_delinquent": False,
            "equity_estimate": 45000,
        }
    ]

    return ingest_leads(
        db,
        source_name="tarrant_county_trustee_connector",
        source_type="trustee_sale_notices",
        leads=leads,
    )


def collin_county_notice_connector(db: Session) -> dict:
    leads = [
        {
            "property_address": "300 Pine St",
            "city": "Plano",
            "state": "TX",
            "foreclosure_stage": "notice_of_default",
            "tax_delinquent": True,
            "equity_estimate": 85000,
        }
    ]

    return ingest_leads(
        db,
        source_name="collin_county_notice_connector",
        source_type="notice_connector",
        leads=leads,
    )
