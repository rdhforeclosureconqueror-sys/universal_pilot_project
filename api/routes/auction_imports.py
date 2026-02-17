from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from io import BytesIO
import os
import csv
import json
import logging
import hashlib
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from db.session import get_db
from ingestion.dallas.dallas_pdf_ingestion import ingest_pdf
from models.auction_import_model import AuctionImport
from models.ingestion_metrics import IngestionMetric

router = APIRouter(prefix="/auction-imports", tags=["Auction Imports"])
logger = logging.getLogger(__name__)


def _load_csv_reader(file):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    decoded = file.file.read().decode("utf-8").splitlines()
    return csv.DictReader(decoded)


def _metric(db: Session, metric_type: str, **kwargs):
    db.add(IngestionMetric(metric_type=metric_type, **kwargs))


@router.post("/upload")
async def upload_auction_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    t0 = datetime.now(timezone.utc)
    contents = await file.read()
    file_hash = hashlib.sha256(contents).hexdigest()

    existing = (
        db.query(AuctionImport)
        .filter(AuctionImport.file_hash == file_hash)
        .order_by(AuctionImport.uploaded_at.desc())
        .first()
    )
    if existing:
        if existing.file_bytes != contents:
            _metric(
                db,
                "file_hash_collision_detected",
                source="auction_import",
                file_hash=file_hash,
                file_name=file.filename,
                count_value=1,
                notes="hash_collision_bytes_mismatch",
            )
        _metric(
            db,
            "duplicate_ingestion_attempt",
            source="auction_import",
            file_hash=file_hash,
            file_name=file.filename,
            count_value=1,
            notes="replay_detected",
        )
        db.commit()
        return {
            "id": str(existing.id),
            "status": existing.status,
            "records_created": existing.records_created,
            "error": existing.error_message,
            "replay": True,
        }

    auction_import = AuctionImport(
        filename=file.filename,
        content_type=file.content_type,
        file_bytes=contents,
        file_type="pdf" if file.filename.lower().endswith(".pdf") else "csv",
        file_hash=file_hash,
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
            created = ingest_pdf(tmp_path, db, source_file_hash=file_hash)
            auction_import.status = "processed"
            auction_import.records_created = created
            _metric(
                db,
                "upload_to_case_creation_seconds",
                source="dallas_pdf",
                file_hash=file_hash,
                file_name=file.filename,
                duration_seconds=(datetime.now(timezone.utc) - t0).total_seconds(),
                count_value=created,
            )
        except Exception as e:
            auction_import.status = "failed"
            auction_import.error_message = str(e)
            auction_import.records_created = 0
            _metric(
                db,
                "parsing_error",
                source="dallas_pdf",
                file_hash=file_hash,
                file_name=file.filename,
                count_value=1,
                notes=str(e)[:200],
            )
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

    try:
        reader = _load_csv_reader(file)
        required_headers = {"external_id", "address", "city", "state", "zip", "auction_date", "opening_bid"}
        missing = required_headers - set(reader.fieldnames or [])
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing headers: {', '.join(missing)}")

        created = 0
        for _row in reader:
            created += 1

        auction_import.status = "processed"
        auction_import.records_created = created
        _metric(
            db,
            "upload_to_case_creation_seconds",
            source="csv",
            file_hash=file_hash,
            file_name=file.filename,
            duration_seconds=(datetime.now(timezone.utc) - t0).total_seconds(),
            count_value=created,
        )
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
        db.add(auction_import)
        _metric(
            db,
            "parsing_error",
            source="csv",
            file_hash=file_hash,
            file_name=file.filename,
            count_value=1,
            notes=str(e)[:200],
        )
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


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
            "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
        }
        for r in records
    ])


@router.get("/auction-files/{import_id}")
def download_auction_file(import_id: str, db: Session = Depends(get_db)):
    record = db.query(AuctionImport).filter(AuctionImport.id == import_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Import not found")
    return StreamingResponse(
        BytesIO(record.file_bytes),
        media_type=record.content_type or "application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{record.filename}"'},
    )


@router.get("/metrics")
def ingestion_metrics(db: Session = Depends(get_db)):
    rows = db.query(IngestionMetric).order_by(IngestionMetric.created_at.desc()).limit(500).all()
    return [
        {
            "metric_type": r.metric_type,
            "source": r.source,
            "file_hash": r.file_hash,
            "file_name": r.file_name,
            "count_value": r.count_value,
            "duration_seconds": r.duration_seconds,
            "notes": r.notes,
            "created_at": r.created_at,
        }
        for r in rows
    ]
