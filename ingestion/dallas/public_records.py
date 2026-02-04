import csv
import json
import re
from dataclasses import dataclass
from io import StringIO
from typing import Iterable
from urllib.request import Request, urlopen


ADDRESS_PATTERN = re.compile(
    r"(?P<address>\d+\s+[^,\n]+),\s*(?P<city>[A-Za-z\s]+),\s*TX\s*(?P<zip>\d{5})",
    re.IGNORECASE,
)


@dataclass
class DallasPublicRecord:
    address: str
    city: str
    state: str
    zip: str
    source: str
    status: str
    county: str = "Dallas"
    trustee: str = ""
    mortgagor: str = ""
    mortgagee: str = ""
    auction_date: Optional[str] = None
    case_number: str = ""
    raw: dict = None


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "universal-pilot-botops"})
    with urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8", errors="ignore")


def _parse_csv(text: str) -> Iterable[DallasPublicRecord]:
    reader = csv.DictReader(StringIO(text))
    for row in reader:
        address = (row.get("Address") or row.get("address") or "").strip()
        city = (row.get("City") or row.get("city") or "Dallas").strip()
        zip_code = (row.get("Zip") or row.get("zip") or "").strip()[:5]
        if not address or not zip_code:
            continue
        yield DallasPublicRecord(
            address=address,
            city=city,
            state=(row.get("State") or row.get("state") or "TX").strip() or "TX",
            zip=zip_code,
            source="dallas_public_records",
            status="pre_foreclosure",
            raw=row,
        )


def _parse_html(text: str) -> Iterable[DallasPublicRecord]:
    for match in ADDRESS_PATTERN.finditer(text):
        yield DallasPublicRecord(
            address=match.group("address").strip(),
            city=match.group("city").strip(),
            state="TX",
            zip=match.group("zip").strip(),
            source="dallas_public_records",
            status="pre_foreclosure",
            raw={"match": match.group(0)},
        )


def fetch_public_records(url: str) -> list[DallasPublicRecord]:
    text = _fetch_text(url)
    if "<html" in text.lower() or "<table" in text.lower():
        records = list(_parse_html(text))
    else:
        records = list(_parse_csv(text))

    if not records:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = []
        if isinstance(payload, list):
            for item in payload:
                address = str(item.get("address") or "").strip()
                zip_code = str(item.get("zip") or "").strip()[:5]
                if not address or not zip_code:
                    continue
                records.append(
                    DallasPublicRecord(
                        address=address,
                        city=str(item.get("city") or "Dallas").strip(),
                        state=str(item.get("state") or "TX").strip(),
                        zip=zip_code,
                        source="dallas_public_records",
                        status="pre_foreclosure",
                        raw=item,
                    )
                )

    return records
