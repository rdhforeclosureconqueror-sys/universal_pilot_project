import logging
from datetime import datetime, timezone
import re

import pdfplumber
from sqlalchemy.orm import Session

from models.ingestion_metrics import IngestionMetric
from ingestion.pdf import extract_text_from_pdf

from .dallas_parser import parse_dallas_row
from .db_writer import write_to_db
from .log_error import log_error
from .normalizer import normalize

logger = logging.getLogger(__name__)


def _rows_from_text(raw_text: str) -> list[list[str]]:
    rows: list[list[str]] = []

    for line in raw_text.splitlines():
        if not line.strip():
            continue

        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
        elif "\t" in line:
            parts = [p.strip() for p in line.split("\t") if p.strip()]
        else:
            parts = [p.strip() for p in re.split(r"\s{2,}", line) if p.strip()]

        if len(parts) >= 9:
            rows.append(parts)

    return rows


def _process_rows(rows: list[list[str]], db: Session) -> tuple[int, int]:
    created = 0
    errors = 0

    for row in rows:
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

    return created, errors


def ingest_pdf(
    pdf_path: str,
    db: Session,
    source_file_hash: str | None = None,
) -> int:
    created = 0
    errors = 0
    t0 = datetime.now(timezone.utc)

    logger.info(f"📄 Starting PDF ingest: {pdf_path}")

    try:
        # --- Primary: Structured table extraction ---
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []

                for table in tables:
                    rows = [row for row in table if row]
                    c, e = _process_rows(rows, db)
                    created += c
                    errors += e

        # --- Fallback: Raw text parsing if no rows created ---
        if created == 0:
            logger.info("No structured tables parsed. Falling back to raw text extraction.")

            raw_text = extract_text_from_pdf(pdf_path)
            rows = _rows_from_text(raw_text)
            c, e = _process_rows(rows, db)
            created += c
            errors += e

        # --- Metrics ---
        duration_seconds = (datetime.now(timezone.utc) - t0).total_seconds()

        db.add(
            IngestionMetric(
                metric_type="pdf_ingestion_summary",
                source="dallas_pdf",
                file_hash=source_file_hash,
                count_value=created,
                duration_seconds=duration_seconds,
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
                    duration_seconds=duration_seconds,
                    notes="row_parse_errors",
                )
            )

        db.commit()

    except Exception:
        db.rollback()
        logger.exception("PDF ingestion failed")
        raise

    logger.info(
        f"✅ PDF ingest complete | created={created} | "
        f"errors={errors} | duration={duration_seconds:.2f}s"
    )

    return created
