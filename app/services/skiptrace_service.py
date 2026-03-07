from __future__ import annotations

from uuid import UUID


def batchdata_adapter(address: str) -> dict:
    return {"owner_name": f"Owner of {address}", "phones": ["+1-214-555-0101"], "emails": ["owner@batchdata.example"]}


def propstream_adapter(address: str) -> dict:
    return {"owner_name": f"Owner of {address}", "phones": ["+1-972-555-0111"], "emails": ["owner@propstream.example"]}


def peopledatalabs_adapter(address: str) -> dict:
    return {"owner_name": f"Owner of {address}", "phones": ["+1-469-555-0121"], "emails": ["owner@pdl.example"]}


ADAPTERS = {
    "batchdata": batchdata_adapter,
    "propstream": propstream_adapter,
    "peopledatalabs": peopledatalabs_adapter,
}


def skiptrace_property_owner(*, address: str, provider: str = "batchdata") -> dict:
    adapter = ADAPTERS.get(provider, batchdata_adapter)
    return adapter(address)


def skiptrace_case_owner(*, case_id: UUID, address: str, provider: str = "batchdata") -> dict:
    data = skiptrace_property_owner(address=address, provider=provider)
    return {"case_id": str(case_id), **data}
