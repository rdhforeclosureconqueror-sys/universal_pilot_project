import logging

import pdfplumber
from sqlalchemy.orm import Session

from .dallas_parser import parse_dallas_row
from .normalizer import normalize
from .db_writer import write_to_db
from .log_error import log_error

logger = logging.getLogger(__name__)

def ingest_pdf(pdf_path: str, db: Session) -> int:
    created = 0
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
                        logger.info(
                            "Persisting Dallas PDF row %s / %s",
                            normalized.get("case_number"),
                            normalized.get("address"),
                        )
                        with db.begin_nested():
                            write_to_db(normalized, db)
                        created += 1
                    except Exception as exc:
                        log_error(row, exc)
    return created
