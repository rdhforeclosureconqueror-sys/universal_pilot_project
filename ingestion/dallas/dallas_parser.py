from typing import List, Optional
from datetime import datetime
import re

# Import your existing utilities if they exist
try:
    from .utils import clean_address, clean_zip, normalize_case_number
except ImportError:
    # Safe fallbacks if utils not available
    def clean_address(value: str) -> str:
        return value.strip() if value else ""

    def clean_zip(value: str) -> str:
        return re.sub(r"[^\d]", "", value)[:5] if value else ""

    def normalize_case_number(value: str) -> str:
        return value.strip() if value else ""


# ------------------------------
# Safe helper functions
# ------------------------------

def _get_cell(cells: List[str], index: int) -> str:
    """Safely return a cell value by index."""
    try:
        value = cells[index]
        return value.strip() if value else ""
    except (IndexError, TypeError):
        return ""


def _is_header_row(cells: List[str]) -> bool:
    """Detect header rows."""
    joined = " ".join(cells).lower()
    return "address" in joined and "zip" in joined


def _is_noise_row(cells: List[str]) -> bool:
    """Detect noise rows like page numbers."""
    joined = " ".join(cells).lower()
    return (
        "page" in joined
        or "dallas county" in joined
        or "trustee" in joined
    )


def _parse_date(value: str) -> Optional[datetime]:
    """Try multiple date formats safely."""
    if not value:
        return None

    formats = [
        "%m/%d/%Y",
        "%m/%d/%y",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue

    return None


def _find_date(cells: List[str]) -> Optional[datetime]:
    """Scan entire row for something that looks like a date."""
    for cell in cells:
        parsed = _parse_date(cell)
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
    opening_bid = _get_cell(cells, 10) if len(cells) > 10 else None

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
