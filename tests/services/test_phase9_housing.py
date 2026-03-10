from types import SimpleNamespace
from uuid import uuid4

from app.services.foreclosure_intelligence_service import calculate_case_priority, create_foreclosure_profile
from app.services.membership_service import create_membership
from app.services.partner_routing_service import route_case_to_partner
from app.services.property_analysis_service import (
    calculate_acquisition_score,
    calculate_equity,
    calculate_ltv,
    calculate_rescue_score,
    classify_intervention,
)
from app.services.property_portfolio_service import calculate_portfolio_equity
from app.services.system_training_service import get_guide_step, get_system_overview, get_workflow_guide


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


def test_foreclosure_case_creation_and_priority():
    case_id = uuid4()
    db = _DB({"ForeclosureCaseData": []})

    profile_result = create_foreclosure_profile(
        db,
        case_id=case_id,
        payload={
            "property_address": "123 Main",
            "foreclosure_stage": "auction_scheduled",
            "arrears_amount": 5000,
            "homeowner_income": 2000,
        },
        actor_id=uuid4(),
    )
    assert str(profile_result["case_id"]) == str(case_id)

    db2 = _DB({"ForeclosureCaseData": [SimpleNamespace(foreclosure_stage="auction_scheduled", arrears_amount=5000, homeowner_income=2000)]})
    priority = calculate_case_priority(db2, case_id=case_id)
    assert priority["priority_tier"] in {"high", "critical"}


def test_equity_calculations_and_classification():
    equity = calculate_equity(estimated_property_value=250000, loan_balance=180000)
    ltv = calculate_ltv(loan_balance=180000, estimated_property_value=250000)
    rescue = calculate_rescue_score(arrears_amount=6000, homeowner_income=2500, foreclosure_stage="notice_of_default")
    acquisition = calculate_acquisition_score(equity=equity, ltv=ltv, foreclosure_stage="auction_scheduled")
    classification = classify_intervention(rescue_score=rescue, acquisition_score=acquisition, ltv=ltv)

    assert equity == 70000
    assert ltv > 0
    assert classification in {"LEGAL_DEFENSE", "LOAN_MODIFICATION", "NONPROFIT_REFERRAL", "ACQUISITION_CANDIDATE"}


def test_partner_routing_logic():
    case_id = uuid4()
    partner = SimpleNamespace(id=uuid4())
    db = _DB({"PartnerOrganization": [partner]})
    referral = route_case_to_partner(db, case_id=case_id, state="TX", routing_category="legal_defense", actor_id=uuid4())
    assert str(referral.case_id) == str(case_id)


def test_portfolio_tracking_summary():
    assets = [
        SimpleNamespace(estimated_value=200000, loan_amount=100000),
        SimpleNamespace(estimated_value=150000, loan_amount=50000),
    ]
    db = _DB({"PropertyAsset": assets})
    summary = calculate_portfolio_equity(db)
    assert summary["total_assets"] == 2
    assert summary["portfolio_equity"] == 200000


def test_membership_creation():
    db = _DB({})
    profile = create_membership(db, user_id=uuid4(), case_id=uuid4(), membership_type="cooperative", actor_id=uuid4())
    assert profile.membership_type == "cooperative"
    assert profile.membership_status == "active"


def test_onboarding_guide_responses():
    overview = get_system_overview()
    workflow = get_workflow_guide()
    step = get_guide_step("property_analysis")

    assert overview["system"] == "Universal Pilot"
    assert len(workflow) >= 7
    assert step is not None
    assert step["related_endpoint"] == "/foreclosure/analyze-property"



def test_create_foreclosure_profile_auto_case(monkeypatch):
    from app.models.policy_versions import PolicyVersion
    from app.models.cases import Case

    policy = SimpleNamespace(id=uuid4(), program_key="training_sandbox")

    class _DBAuto(_DB):
        def __init__(self):
            super().__init__({"ForeclosureCaseData": [], "PolicyVersion": [policy]})

    db = _DBAuto()

    # patch query behavior for Case add/flush result id assignment approximation
    created_cases = []
    old_add = db.add

    def _add(obj):
        if obj.__class__.__name__ == Case.__name__ and not getattr(obj, "id", None):
            obj.id = uuid4()
            created_cases.append(obj)
        old_add(obj)

    db.add = _add

    result = create_foreclosure_profile(
        db,
        case_id=None,
        payload={
            "property_address": "123 Main St",
            "city": "Dallas",
            "state": "TX",
            "loan_balance": 210000,
            "estimated_property_value": 320000,
            "arrears_amount": 15000,
            "foreclosure_stage": "pre_foreclosure",
        },
        actor_id=uuid4(),
    )

    assert result["profile_created"] is True
    assert result["case_id"] is not None
