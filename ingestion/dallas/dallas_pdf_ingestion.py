import logging
import pdfplumber
from sqlalchemy.orm import Session

from .dallas_parser import parse_dallas_row
from .normalizer import normalize
from .db_writer import write_to_db
from .log_error import log_error

logger = logging.getLogger(__name__)

def ingest_pdf(pdf_path: str, db: Session) -> int:
    """
    Ingests a Dallas County PDF and writes valid rows to the database.

    Args:
        pdf_path (str): Path to the PDF file.
        db (Session): SQLAlchemy DB session.

    Returns:
        int: Number of records successfully created.
    """
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
                            "Persisting Dallas PDF row: Case %s | Address %s",
                            normalized.get("case_number"),
                            normalized.get("address"),
                        )
                        with db.begin_nested():  # Safe transaction block
                            write_to_db(normalized, db)
                        created += 1
                    except Exception as exc:
                        log_error(row, exc)  # Log individual row error but continue
    return created
