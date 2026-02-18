from __future__ import annotations

from typing import List, Optional

from .utils import clean_address, clean_zip, normalize_case_number, parse_date


def _normalize_row(row: List[str]) -> list[str]:
    return [str(cell or "").strip() for cell in row if str(cell or "").strip()]


def _get_cell(cells: list[str], index: int) -> str:
    if index < 0 or index >= len(cells):
        return ""
    return cells[index] or ""


def _is_header_row(cells: list[str]) -> bool:
    token = " ".join(cells).lower()
    return "address" in token and "zip" in token


def _is_noise_row(cells: list[str]) -> bool:
    token = " ".join(cells).lower()
    noise_markers = ["cause no", "page", "dallas county", "trustee sale"]
    return any(marker in token for marker in noise_markers)


def _find_date(cells: list[str]):
    for cell in cells:
        parsed = parse_date(cell)
        if parsed:
            return parsed
    return None


# ------------------------------
# Main Parser
# ------------------------------

def parse_dallas_row(row: List[str]) -> Optional[dict]:
    """
    Parse a single row of Dallas auction data.
    Returns dictionary or None if invalid.
    """

    if not row:
        return None

    cells = row

    # Skip headers and noise
    if _is_header_row(cells) or _is_noise_row(cells):
        return None

    # Extract by position (defensive)
    address = clean_address(_get_cell(cells, 0))
    city = _get_cell(cells, 1) or "Dallas"
    state = _get_cell(cells, 2) or "TX"
    zip_code = clean_zip(_get_cell(cells, 3))
    county = _get_cell(cells, 4) or "Dallas"
    trustee = _get_cell(cells, 5)
    mortgagor = _get_cell(cells, 6)
    mortgagee = _get_cell(cells, 7)
    auction_date = _parse_date(_get_cell(cells, 8))
    case_number = normalize_case_number(_get_cell(cells, 9))
    opening_bid = _get_cell(cells, 10).strip() if len(cells) > 10 else None

    # Fallback: search entire row for date
    if not auction_date:
        auction_date = _find_date(cells)

    # Minimum requirement: address only
    # (Relaxed so ingestion actually works)
    if not address:
        return None

    return {
        "address": address,
        "city": city,
        "state": state,
        "zip": zip_code,
        "county": county,
        "trustee": trustee,
        "mortgagor": mortgagor,
        "mortgagee": mortgagee,
        "auction_date": auction_date,
        "case_number": case_number,
        "opening_bid": opening_bid,
        "source": "dallas_county_pdf",
    }
