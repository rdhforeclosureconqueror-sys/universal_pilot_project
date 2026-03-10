from types import SimpleNamespace
from uuid import uuid4

from app.services.essential_worker_housing_service import (
    discover_housing_programs,
    generate_homebuyer_action_plan,
    upsert_worker_profile,
)


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return list(self.rows)

    def delete(self):
        return None


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


def test_discover_benefits_for_nurse():
    profile = SimpleNamespace(id=uuid4(), profession="nurse", state="TX")
    db = _DB({"EssentialWorkerProfile": [profile], "EssentialWorkerBenefitMatch": []})

    result = discover_housing_programs(db, profile_id=profile.id)

    assert result["total_estimated_benefits"] > 0
    assert any(p["program"] == "Good Neighbor Next Door" for p in result["eligible_programs"])


def test_upsert_worker_profile_and_action_plan():
    db = _DB({"EssentialWorkerProfile": [], "EssentialWorkerBenefitMatch": [SimpleNamespace(program="Sample Program")]})
    profile = upsert_worker_profile(db, payload={"profession": "teacher", "state": "TX"}, actor_id=uuid4())
    assert profile.profession == "teacher"

    # patch query map for profile-specific action plan call
    db2 = _DB({"EssentialWorkerBenefitMatch": [SimpleNamespace(program="Sample Program")]})
    plan = generate_homebuyer_action_plan(db2, profile_id=uuid4())
    assert any("Apply for" in step for step in plan["steps"])
