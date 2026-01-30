import csv
import json
import logging
import os
import pdfplumber
from datetime import datetime
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from models.properties import Property
from models.cases import Case
from models.ai_scores import AIScore
from models.enums import CaseStatus
from audit.logger import log_audit
from ai.logger import log_ai_activity
from ingestion.dallas.dallas_pdf_ingestion import ingest_pdf

router = APIRouter(prefix="/imports", tags=["Imports"])
logger = logging.getLogger(__name__)


def _parse_int(value):
    if value in (None, ""):
        return None
    return int(float(value))


def _parse_float(value):
    if value in (None, ""):
        return None
    return float(value)


def _parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d")


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
        strategy = "HIGH_EQUITY_INTERVENTION"
    elif equity > 30000:
        strategy = "NEGOTIATION_TARGET"
    else:
        strategy = "MONITOR_ONLY"
    return equity, strategy


def _load_csv_reader(file: UploadFile):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    decoded = file.file.read().decode("utf-8").splitlines()
    return csv.DictReader(decoded)


@router.post("/auction")
@router.post("/auction-csv")
def import_auction_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        if file.filename.lower().endswith(".pdf"):
            with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(file.file.read())
                temp_path = temp_file.name
            try:
                created = ingest_pdf(temp_path, db)
                db.commit()
                logger.info("Committed Dallas PDF ingestion (%s records)", created)
            except Exception:
                db.rollback()
                raise
            finally:
                os.unlink(temp_path)
            return {
                "status": "success",
                "message": "PDF ingestion completed",
                "records_created": created,
            }

        reader = _load_csv_reader(file)
        required_headers = {
            "external_id",
            "address",
            "city",
            "state",
            "zip",
            "auction_date",
            "opening_bid",
        }
        incoming_headers = set(reader.fieldnames or [])
        missing_headers = required_headers - incoming_headers
        if missing_headers:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required headers: {', '.join(sorted(missing_headers))}",
            )

        created = 0

        for row in reader:
            address_line = f"{row.get('address', '')}, {row.get('city', '')}, {row.get('state', '')} {row.get('zip', '')}".strip()
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
            if equity is not None and strategy is not None:
                ai_score = AIScore(
                    id=uuid4(),
                    case_id=case.id,
                    equity=equity,
                    strategy=strategy,
                    confidence=0.92,
                )
                db.add(ai_score)
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

        db.commit()
        return {"status": "success", "records_created": created}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Auction CSV import failed")
        raise HTTPException(status_code=500, detail=str(exc))
