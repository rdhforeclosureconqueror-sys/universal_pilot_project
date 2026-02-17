import logging
from datetime import datetime, timezone

import pdfplumber
from sqlalchemy.orm import Session

from models.ingestion_metrics import IngestionMetric

from .dallas_parser import parse_dallas_row
from .db_writer import write_to_db
from .log_error import log_error
from .normalizer import normalize

logger = logging.getLogger(__name__)


def ingest_pdf(pdf_path: str, db: Session, source_file_hash: str | None = None) -> int:
    created = 0
    errors = 0
    t0 = datetime.now(timezone.utc)

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    if not row:
                        continue
                    try:
                        record = parse_dallas_row(row)
                        if record is None:
                            continue
                        normalized = normalize(record)

                        with db.begin_nested():
                            write_to_db(normalized, db)
                        created += 1
                    except Exception as exc:
                        errors += 1
                        log_error(row, exc)

    db.add(
        IngestionMetric(
            metric_type="pdf_ingestion_summary",
            source="dallas_pdf",
            file_hash=source_file_hash,
            count_value=created,
            duration_seconds=(datetime.now(timezone.utc) - t0).total_seconds(),
            notes=f"errors={errors}",
        )
    )
    if errors:
        db.add(
            IngestionMetric(
                metric_type="parsing_error_rate",
                source="dallas_pdf",
                file_hash=source_file_hash,
                count_value=errors,
                duration_seconds=(datetime.now(timezone.utc) - t0).total_seconds(),
                notes="row_parse_errors",
            )
        )
    return created
