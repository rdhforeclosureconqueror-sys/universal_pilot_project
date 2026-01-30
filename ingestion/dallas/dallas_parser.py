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


def _is_noise_row(cells: List[str]) -> bool:
    tokens = " ".join(cells).upper()
    if "EQUITY" in tokens or "MARGIN" in tokens:
        return True
    return all(
        any(char.isdigit() for char in cell) and not any(char.isalpha() for char in cell)
        for cell in cells
    )


def _find_date(cells: List[str]):
    for cell in cells:
        parsed = parse_date(cell)
        if parsed:
            return parsed
    return None


def parse_dallas_row(row: List[str]) -> Optional[dict]:
    cells = _normalize_row(row)
    if not cells:
        return None

    if _is_header_row(cells):
        return None

    if _is_noise_row(cells):
        return None

    address = clean_address(_get_cell(cells, 0))
    city = _get_cell(cells, 1).strip() if len(cells) > 1 else "Dallas"
    state = _get_cell(cells, 2).strip() if len(cells) > 2 else "TX"
    zip_code = clean_zip(_get_cell(cells, 3) if len(cells) > 3 else " ".join(cells))
    county = _get_cell(cells, 4).strip() if len(cells) > 4 else "Dallas"
    trustee = _get_cell(cells, 5).strip() if len(cells) > 5 else ""
    mortgagor = _get_cell(cells, 6).strip() if len(cells) > 6 else ""
    mortgagee = _get_cell(cells, 7).strip() if len(cells) > 7 else ""
    auction_date = parse_date(_get_cell(cells, 8)) if len(cells) > 8 else None
    source = _get_cell(cells, 9).strip() if len(cells) > 9 else "dallas_county_pdf"

    case_number = normalize_case_number(_get_cell(cells, 10)) if len(cells) > 10 else ""

    if not auction_date:
        auction_date = _find_date(cells)

    if not address or not zip_code or not auction_date:
        return None

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
        "source": source or "dallas_county_pdf",
    }
