from .utils import clean_address


def normalize(record: dict) -> dict:
    normalized = dict(record)
    normalized["address"] = clean_address(record.get("address", ""))
    normalized["city"] = "Dallas"
    normalized["state"] = "TX"
    normalized["status"] = "auction_intake"

    case_number = record.get("case_number") or ""
    normalized["external_id"] = f"dallas_county_pdf:{case_number}" if case_number else "dallas_county_pdf"

    normalized.setdefault("zip", "")
    normalized.setdefault("opening_bid", None)
    normalized.setdefault("parcel_id", None)
    normalized.setdefault("county", "Dallas")
    normalized.setdefault("mortgagor", record.get("defendant"))
    normalized.setdefault("mortgagee", record.get("plaintiff"))

    return normalized
