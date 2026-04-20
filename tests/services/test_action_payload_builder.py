from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.action_payload_builder import ActionExecutionContext, build_action_payload


def test_create_case_from_lead_injects_actor_from_context():
    actor_id = uuid4()
    lead_id = uuid4()

    payload = build_action_payload(
        "create_case_from_lead",
        {"lead_id": str(lead_id)},
        context=ActionExecutionContext(actor_id=actor_id),
    )

    assert payload["lead_id"] == str(lead_id)
    assert payload["actor_id"] == actor_id


def test_route_case_partner_uses_context_defaults():
    case_id = uuid4()

    payload = build_action_payload(
        "route-case-partner",
        {},
        context=ActionExecutionContext(case_id=case_id, state="CA"),
    )

    assert payload["case_id"] == case_id
    assert payload["state"] == "CA"
    assert payload["routing_category"] == "nonprofit_support"


def test_validation_error_is_structured_when_missing_required_fields():
    with pytest.raises(HTTPException) as err:
        build_action_payload(
            "analyze_property",
            {"loan_balance": 100000},
            context=ActionExecutionContext(),
        )

    assert err.value.status_code == 400
    assert err.value.detail["error"] == "action_payload_validation_failed"
    assert "case_id" in err.value.detail["missing_fields"]
