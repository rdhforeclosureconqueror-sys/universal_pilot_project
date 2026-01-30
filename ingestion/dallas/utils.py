from datetime import datetime
import re


def clean_address(raw_address: str) -> str:
    if raw_address is None:
        return ""
    cleaned = re.sub(r"\s+", " ", raw_address.strip())
    return cleaned


def normalize_case_number(case_number: str) -> str:
    if case_number is None:
        return ""
    cleaned = re.sub(r"\s+", " ", case_number.strip())
    return cleaned.upper()


def parse_date(raw_date: str) -> datetime:
    if raw_date is None:
        raise ValueError("Missing auction date")
    cleaned = raw_date.strip()
    if not cleaned:
        raise ValueError("Missing auction date")

    date_formats = ["%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%B %d, %Y"]
    for fmt in date_formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {raw_date}")
