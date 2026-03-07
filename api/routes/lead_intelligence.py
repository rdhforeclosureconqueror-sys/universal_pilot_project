from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from db.session import get_db
from app.services.lead_intelligence_service import ingest_leads, score_property_lead


router = APIRouter(prefix="/leads/intelligence", tags=["Lead Intelligence"])


class LeadIngestRequest(BaseModel):
    source_name: str
    source_type: str
    leads: list[dict]


class LeadScoreRequest(BaseModel):
    lead_id: UUID


@router.post("/ingest")
def ingest(
    request: LeadIngestRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    return ingest_leads(db, source_name=request.source_name, source_type=request.source_type, leads=request.leads)


@router.post("/score")
def score(
    request: LeadScoreRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    return score_property_lead(db, lead_id=request.lead_id)


@router.post("/ingest-csv")
def ingest_csv(
    source_name: str,
    source_type: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    sample = [{"property_address": "400 Cedar St", "city": "Dallas", "state": "TX", "foreclosure_stage": "pre_foreclosure", "auction_date": datetime.now(timezone.utc)}]
    return ingest_leads(db, source_name=source_name, source_type=source_type, leads=sample)
