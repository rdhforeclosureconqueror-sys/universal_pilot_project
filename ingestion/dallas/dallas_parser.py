from typing import List

from .utils import clean_address, normalize_case_number, parse_date


EXPECTED_COLUMNS = 6


def _get_cell(row: List[str], index: int) -> str:
    if index >= len(row):
        return ""
    return row[index] or ""


def parse_dallas_row(row: List[str]) -> dict:
    if len(row) < EXPECTED_COLUMNS:
        raise ValueError(f"Expected at least {EXPECTED_COLUMNS} columns, received {len(row)}")

    address = clean_address(_get_cell(row, 0))
    case_number = normalize_case_number(_get_cell(row, 1))
    plaintiff = _get_cell(row, 2).strip()
    defendant = _get_cell(row, 3).strip()
    auction_date = parse_date(_get_cell(row, 4))
    trustee = _get_cell(row, 5).strip()

    if not address or not case_number:
        raise ValueError("Missing required address or case number")

    return {
        "address": address,
        "case_number": case_number,
        "plaintiff": plaintiff,
        "defendant": defendant,
        "auction_date": auction_date,
        "trustee": trustee,
        "source": "dallas_county_pdf",
    }
