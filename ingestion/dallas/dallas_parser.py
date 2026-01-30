from typing import List, Optional

from .utils import clean_address, normalize_case_number, parse_date, clean_zip


EXPECTED_COLUMNS = 9
HEADER_TOKENS = {
    "address",
    "city",
    "state",
    "zip",
    "county",
    "trustee",
    "mortgagor",
    "mortgagee",
    "auction",
    "date",
}


def _get_cell(row: List[str], index: int) -> str:
    if index >= len(row):
        return ""
    return row[index] or ""


def _normalize_row(row: List[str]) -> List[str]:
    return [str(cell or "").strip() for cell in row if str(cell or "").strip()]


def _is_header_row(cells: List[str]) -> bool:
    lowered = {cell.lower() for cell in cells}
    return any(token in lowered for token in HEADER_TOKENS)


def parse_dallas_row(row: List[str]) -> Optional[dict]:
    cells = _normalize_row(row)
    if not cells:
        return None

    if _is_header_row(cells):
        return None

    if len(cells) < EXPECTED_COLUMNS:
        raise ValueError(
            f"Expected at least {EXPECTED_COLUMNS} columns, received {len(cells)}"
        )

    address = clean_address(_get_cell(cells, 0))
    city = _get_cell(cells, 1).strip()
    state = _get_cell(cells, 2).strip()
    zip_code = clean_zip(_get_cell(cells, 3))
    county = _get_cell(cells, 4).strip()
    trustee = _get_cell(cells, 5).strip()
    mortgagor = _get_cell(cells, 6).strip()
    mortgagee = _get_cell(cells, 7).strip()
    auction_date = parse_date(_get_cell(cells, 8))
    source = _get_cell(cells, 9).strip() if len(cells) > 9 else "dallas_county_pdf"

    case_number = normalize_case_number(_get_cell(cells, 10)) if len(cells) > 10 else ""

    if not address or not city or not state or not zip_code or not auction_date:
        raise ValueError("Missing required address, city, state, zip, or auction date")

    

    return {
        "address": address,
        "case_number": case_number,
        "city": city,
        "state": state,
        "zip": zip_code,
        "county": county,
        "trustee": trustee,
        "mortgagor": mortgagor,
        "mortgagee": mortgagee,
        "auction_date": auction_date,
        "source": source,
    }
