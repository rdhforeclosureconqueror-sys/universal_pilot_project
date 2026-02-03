from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4
import os
import csv
import json
import logging
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from db.session import get_db
from ingestion.dallas.dallas_pdf_ingestion import ingest_pdf
from models.auction_import_model import AuctionImport
from models.properties import Property
from models.cases import Case
from models.ai_scores import AIScore
from models.deal_scores import DealScore
from models.enums import CaseStatus
from audit.logger import log_audit
from ai.logger import log_ai_activity

router = APIRouter(prefix="/auction-imports", tags=["Auction Imports"])
logger = logging.getLogger(__name__)

# Utility parsing functions
def _parse_int(value): return int(float(value)) if value not in (None, "") else None
def _parse_float(value): return float(value) if value not in (None, "") else None
def _parse_date(value): return datetime.strptime(value, "%Y-%m-%d") if value else None

def _geocode_address(address):
    if not address:
        return None, None
    query = urlencode({"q": address, "format": "json", "limit": 1})
    url = f"https://nominatim.openstreetmap.org/search?{query}"
    request = Request(url, headers={"User-Agent": "universal-pilot-crm"})
    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload:
        return None, None
    return float(payload[0]["lat"]), float(payload[0]["lon"])

def _calculate_strategy(assessed_value, est_balance):
    if assessed_value is None or est_balance is None:
        return None, None
    equity = assessed_value - est_balance
    if equity > 100000:
        return equity, "HIGH_EQUITY_INTERVENTION"
    elif equity > 30000:
        return equity, "NEGOTIATION_TARGET"
    return equity, "MONITOR_ONLY"

def _deal_tier(score): return "A" if score >= 80 else "B" if score >= 60 else "C"

def _deal_exit_strategy(equity, urgency_days):
    if urgency_days is not None and urgency_days <= 7:
        return "AUCTION_RUSH"
    if equity is not None and equity >= 100000:
        return "HOLD_OR_FLIP"
    if urgency_days is not None and urgency_days <= 30:
        return "NEGOTIATE"
    return "MONITOR"

def _deal_score(equity, urgency_days):
    score = 50
    if equity is not None:
        score += 30 if equity >= 150000 else 20 if equity >= 75000 else 10 if equity >= 30000 else 0
    if urgency_days is not None:
        score += 20 if urgency_days <= 7 else 10 if urgency_days <= 30 else 5 if urgency_days <= 90 else 0
    score = max(0, min(100, score))
    return score, _deal_tier(score), _deal_exit_strategy(equity, urgency_days), urgency_days

def _load_csv_reader(file):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    decoded = file.file.read().decode("utf-8").splitlines()
    return csv.DictReader(decoded)

# ✅ Main Upload Route (PDF or CSV)
@router.post("/upload")
async def upload_auction_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()

    auction_import = AuctionImport(
        filename=file.filename,
        content_type=file.content_type,
        file_bytes=contents,
        file_type="pdf" if file.filename.endswith(".pdf") else "csv",
        status="received",
        uploaded_at=datetime.utcnow(),
    )
    db.add(auction_import)
    db.commit()
    db.refresh(auction_import)

    if file.filename.lower().endswith(".pdf"):
        tmp_path = f"/tmp/{file.filename}"
        with open(tmp_path, "wb") as f:
            f.write(contents)
        try:
            created = ingest_pdf(tmp_path, db)
            auction_import.status = "processed"
            auction_import.records_created = created
        except Exception as e:
            auction_import.status = "failed"
            auction_import.error_message = str(e)
            auction_import.records_created = 0
        finally:
            db.commit()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        return {
            "id": str(auction_import.id),
            "status": auction_import.status,
            "records_created": auction_import.records_created,
            "error": auction_import.error_message,
        }

    # CSV Processing
    try:
        reader = _load_csv_reader(file)
        required_headers = {
            "external_id", "address", "city", "state", "zip", "auction_date", "opening_bid"
        }
        missing = required_headers - set(reader.fieldnames or [])
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing headers: {', '.join(missing)}")

        created = 0
        for row in reader:
            address_line = f"{row.get('address')}, {row.get('city')}, {row.get('state')} {row.get('zip')}".strip()
            latitude, longitude = _geocode_address(address_line)

            prop = Property(
                external_id=row["external_id"],
                address=row["address"],
                city=row["city"],
                state=row["state"],
                zip=row["zip"],
                county=row.get("county"),
                property_type=row.get("property_type"),
                year_built=_parse_int(row.get("year_built")),
                sqft=_parse_int(row.get("sqft")),
                beds=_parse_float(row.get("beds")),
                baths=_parse_float(row.get("baths")),
                assessed_value=_parse_int(row.get("assessed_value")),
                mortgagor=row.get("mortgagor"),
                mortgagee=row.get("mortgagee"),
                trustee=row.get("trustee"),
                loan_type=row.get("loan_type"),
                interest_rate=_parse_float(row.get("interest_rate")),
                orig_loan_amount=_parse_int(row.get("orig_loan_amount")),
                est_balance=_parse_int(row.get("est_balance")),
                auction_date=_parse_date(row.get("auction_date")),
                auction_time=row.get("auction_time"),
                source=row.get("source"),
                latitude=latitude,
                longitude=longitude,
            )
            db.add(prop)
            db.flush()

            case = Case(
                id=uuid4(),
                status=CaseStatus.auction_intake,
                created_by=uuid4(),
                program_type="FORECLOSURE_PREVENTION",
                property_id=prop.id,
            )
            db.add(case)

            equity, strategy = _calculate_strategy(prop.assessed_value, prop.est_balance)
            if equity is not None and strategy:
                db.add(AIScore(
                    id=uuid4(),
                    case_id=case.id,
                    equity=equity,
                    strategy=strategy,
                    confidence=0.92,
                ))
                log_ai_activity(
                    db=db,
                    case_id=str(case.id),
                    policy_version_id=None,
                    ai_role="advisory",
                    model_provider="rules",
                    model_name="equity-strategy",
                    model_version="v1",
                    prompt_hash="auction_csv_import",
                    policy_rule_id="auction_strategy_v1",
                    confidence_score=0.92,
                )

            urgency_days = (prop.auction_date.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days if prop.auction_date else None
            score, tier, exit_strategy, urgency_days = _deal_score(equity, urgency_days)

            db.add(DealScore(
                id=uuid4(),
                property_id=prop.id,
                case_id=case.id,
                score=score,
                tier=tier,
                exit_strategy=exit_strategy,
                urgency_days=urgency_days,
            ))

            log_audit(
                db=db,
                case_id=str(case.id),
                actor_id=None,
                action_type="auction_property_imported",
                reason_code="auction_csv_import",
                before_state={},
                after_state={
                    "property_id": str(prop.id),
                    "external_id": prop.external_id,
                    "case_status": case.status.value,
                },
                policy_version_id=None,
            )
            created += 1

        auction_import.status = "processed"
        auction_import.records_created = created
        db.commit()

        return {
            "id": str(auction_import.id),
            "status": auction_import.status,
            "records_created": created,
            "error": None,
        }

    except Exception as e:
        db.rollback()
        auction_import.status = "failed"
        auction_import.error_message = str(e)
        auction_import.records_created = 0
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


# ✅ List Auction Imports (used by frontend)
@router.get("/auction-files", name="get_auction_imports")
@router.get("/imports/auction-files", include_in_schema=False)
async def get_auction_imports(db: Session = Depends(get_db)):
    records = db.query(AuctionImport).order_by(AuctionImport.uploaded_at.desc()).all()
    return jsonable_encoder([
        {
            "id": str(r.id),
            "filename": r.filename,
            "status": r.status,
            "records_created": r.records_created,
            "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None
        } for r in records
    ])


# ✅ File Download
@router.get("/auction-files/{import_id}")
def download_auction_file(import_id: str, db: Session = Depends(get_db)):
    record = db.query(AuctionImport).filter(AuctionImport.id == import_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Import not found")
    return StreamingResponse(
        BytesIO(record.file_bytes),
        media_type=record.content_type or "application/pdf",
        headers={"Content-Disposition": f'attachment; filename=\"{record.filename}\"'}
    )
