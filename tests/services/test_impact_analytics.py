from types import SimpleNamespace
from uuid import uuid4

from app.services import impact_analytics_service
from app.services.veteran_intelligence_service import calculate_benefit_value


class _QueryStub:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _DBStub:
    def __init__(self, registry_rows):
        self._registry_rows = registry_rows

    def query(self, model):
        del model
        return _QueryStub(self._registry_rows)


def test_benefit_value_calculation(monkeypatch):
    case_id = uuid4()

    def _match_benefits(_db, *, case_id):
        return {
            "eligible_benefits": ["VA_HOME_LOAN", "VA_IRRRL_REFINANCE"],
            "estimated_total_value": 0,
            "priority_order": [],
            "categories": [],
        }

    monkeypatch.setattr("app.services.veteran_intelligence_service.match_benefits", _match_benefits)

    db = _DBStub(
        [
            SimpleNamespace(benefit_name="VA_HOME_LOAN", estimated_value=12000.0),
            SimpleNamespace(benefit_name="VA_IRRRL_REFINANCE", estimated_value=6000.0),
        ]
    )

    result = calculate_benefit_value(db, case_id=case_id)

    assert result["annual_total"] == 18000.0
    assert result["monthly_total"] == 1500.0
    assert result["lifetime_total"] == 540000.0


def test_impact_summary_generation(monkeypatch):
    monkeypatch.setattr(
        impact_analytics_service,
        "_collect_case_impact_rows",
        lambda _db: [
            {
                "state": "TX",
                "benefits_discovered": 3,
                "benefits_claimed": 2,
                "benefit_value_discovered": 22000.0,
                "benefit_value_unlocked": 10000.0,
                "foreclosure_prevented": True,
            },
            {
                "state": "CA",
                "benefits_discovered": 2,
                "benefits_claimed": 1,
                "benefit_value_discovered": 12000.0,
                "benefit_value_unlocked": 4000.0,
                "foreclosure_prevented": False,
            },
        ],
    )

    summary = impact_analytics_service.get_impact_summary(db=None)

    assert summary["veterans_served"] == 2
    assert summary["benefits_discovered"] == 5
    assert summary["benefits_claimed"] == 3
    assert summary["benefit_value_unlocked"] == 14000.0
    assert summary["foreclosures_prevented"] == 1


def test_opportunity_map_aggregation(monkeypatch):
    monkeypatch.setattr(
        impact_analytics_service,
        "_collect_case_impact_rows",
        lambda _db: [
            {
                "state": "TX",
                "benefits_discovered": 3,
                "benefits_claimed": 2,
                "benefit_value_discovered": 22000.0,
                "benefit_value_unlocked": 10000.0,
                "foreclosure_prevented": True,
            },
            {
                "state": "TX",
                "benefits_discovered": 1,
                "benefits_claimed": 1,
                "benefit_value_discovered": 5000.0,
                "benefit_value_unlocked": 5000.0,
                "foreclosure_prevented": False,
            },
            {
                "state": "CA",
                "benefits_discovered": 2,
                "benefits_claimed": 1,
                "benefit_value_discovered": 12000.0,
                "benefit_value_unlocked": 4000.0,
                "foreclosure_prevented": False,
            },
        ],
    )

    mapped = impact_analytics_service.get_opportunity_map(db=None)

    assert mapped[0]["state"] == "TX"
    assert mapped[0]["veterans_served"] == 2
    assert mapped[0]["benefit_value_discovered"] == 27000.0
    assert mapped[0]["benefits_claimed"] == 3
