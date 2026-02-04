from typing import List, Optional

def parse_dallas_row(row: List[str]) -> Optional[dict]:
    """
    Parse a single row of Dallas auction data from a PDF or CSV source.

    Args:
        row (List[str]): A list of strings representing the row cells.

    Returns:
        Optional[dict]: A dictionary with normalized auction data or None if invalid.
    """
    cells = _normalize_row(row)
    if not cells:
        return None

    if _is_header_row(cells) or _is_noise_row(cells):
        return None

    # Map expected values by position
    address = clean_address(_get_cell(cells, 0))
    city = _get_cell(cells, 1).strip() or "Dallas"
    state = _get_cell(cells, 2).strip() or "TX"
    zip_code = clean_zip(_get_cell(cells, 3))
    county = _get_cell(cells, 4).strip() or "Dallas"
    trustee = _get_cell(cells, 5).strip()
    mortgagor = _get_cell(cells, 6).strip()
    mortgagee = _get_cell(cells, 7).strip()
    auction_date = parse_date(_get_cell(cells, 8))
    case_number = normalize_case_number(_get_cell(cells, 9))
    opening_bid = _get_cell(cells, 10).strip() if len(cells) > 10 else None

    # Fallback: scan for auction date if it wasn't parsed directly
    if not auction_date:
        auction_date = _find_date(cells)

    if not address or not zip_code or not auction_date:
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
