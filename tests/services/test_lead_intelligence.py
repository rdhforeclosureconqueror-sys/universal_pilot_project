from types import SimpleNamespace
from uuid import uuid4

from app.services.lead_intelligence_service import deduplicate_leads, ingest_leads, score_property_lead


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return list(self.rows)


class _DB:
    def __init__(self, model_map):
        self.model_map = model_map
        self.added = []

    def query(self, model):
        return _Query(self.model_map.get(model.__name__, []))

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        return None


def test_ingest_leads_and_deduplicate():
    source = SimpleNamespace(id=uuid4(), source_name="manual", source_type="manual")
    db = _DB({"LeadSource": [source], "PropertyLead": []})

    result = ingest_leads(
        db,
        source_name="manual",
        source_type="manual",
        leads=[{"property_address": "1 A St", "city": "Dallas", "state": "TX", "foreclosure_stage": "pre_foreclosure"}],
    )
    assert result["leads_ingested"] == 1

    # duplicate detection path
    db2 = _DB({"PropertyLead": [SimpleNamespace()]})
    assert deduplicate_leads(db2, source_id=uuid4(), property_address="1 A St") is True


def test_score_property_lead_returns_grade(monkeypatch):
    lead = SimpleNamespace(
        id=uuid4(),
        foreclosure_stage="auction_scheduled",
        tax_delinquent="true",
        equity_estimate=70000,
        auction_date=None,
        owner_occupancy="true",
        property_address="1 A St",
        city="Dallas",
        state="TX",
    )
    policy = SimpleNamespace(id=uuid4(), program_key="training_sandbox")

    db = _DB({"PropertyLead": [lead], "PolicyVersion": [policy]})
    result = score_property_lead(db, lead_id=lead.id)
    assert result["grade"] in {"A", "B", "C"}
