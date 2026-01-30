import hashlib

from .utils import clean_address


def normalize(record: dict) -> dict:
    normalized = dict(record)
    normalized["address"] = clean_address(record.get("address", ""))
    normalized["city"] = record.get("city") or "Dallas"
    normalized["state"] = record.get("state") or "TX"
    normalized["status"] = "auction_intake"

    auction_date = record.get("auction_date")
    date_token = auction_date.isoformat() if auction_date else "unknown"
    identity = f"{normalized['address']}|{normalized.get('zip','')}|{date_token}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    normalized["external_id"] = f"dallas_county_pdf:{digest}"

    normalized.setdefault("zip", "")
    normalized.setdefault("opening_bid", None)
    normalized.setdefault("parcel_id", None)
    normalized.setdefault("county", "Dallas")
    normalized.setdefault("mortgagor", record.get("mortgagor"))
    normalized.setdefault("mortgagee", record.get("mortgagee"))

    return normalized
