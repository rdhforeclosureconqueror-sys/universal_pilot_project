import pdfplumber

from .dallas_parser import parse_dallas_row
from .normalizer import normalize
from .db_writer import write_to_db
from .log_error import log_error


def ingest_pdf(pdf_path: str) -> None:
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    if not row:
                        continue
                    try:
                        record = parse_dallas_row(row)
                        normalized = normalize(record)
                        write_to_db(normalized)
                    except Exception as exc:
                        log_error(row, exc)
