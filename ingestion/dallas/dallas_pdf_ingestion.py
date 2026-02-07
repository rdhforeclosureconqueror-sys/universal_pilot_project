import logging
import re

import pdfplumber
from sqlalchemy.orm import Session

from ingestion.pdf import extract_text_from_pdf

from .dallas_parser import parse_dallas_row
from .normalizer import normalize
from .db_writer import write_to_db
from .log_error import log_error

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


def _process_rows(rows: list[list[str]], db: Session) -> int:
    created = 0
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
            log_error(row, exc)
    return created


def ingest_pdf(pdf_path: str, db: Session) -> int:
    created = 0
    print(f"📄 Starting PDF ingest: {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                created += _process_rows([row for row in table if row], db)

    if created == 0:
        raw_text = extract_text_from_pdf(pdf_path)
        rows = _rows_from_text(raw_text)
        created = _process_rows(rows, db)

    print(f"✅ PDF ingest complete. Records created: {created}")
    return created
