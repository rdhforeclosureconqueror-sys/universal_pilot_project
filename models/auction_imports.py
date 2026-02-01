from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import shutil
import os

from db.session import get_db
from ingestion.dallas.dallas_pdf_ingestion import ingest_pdf

router = APIRouter(prefix="/auction-imports", tags=["Auction Imports"])


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    contents = await file.read()

    # Import AuctionImport inside the function to avoid circular import
    from models.auction_imports import AuctionImport

    import_record = AuctionImport(
        filename=file.filename,
        content_type=file.content_type,
        file_bytes=contents,
        status="received",
    )

    db.add(import_record)
    db.commit()
    db.refresh(import_record)

    # Save file temporarily to disk for pdfplumber
    tmp_path = f"/tmp/{file.filename}"
    with open(tmp_path, "wb") as f:
        f.write(contents)

    try:
        created = ingest_pdf(tmp_path, db)
        import_record.status = "processed"
        import_record.records_created = created
        import_record.error_message = None
    except Exception as e:
        import_record.status = "failed"
        import_record.error_message = str(e)
        import_record.records_created = 0
    finally:
        db.commit()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return {
        "id": str(import_record.id),
        "status": import_record.status,
        "records_created": import_record.records_created,
        "error": import_record.error_message,
    }
