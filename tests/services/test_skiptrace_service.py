from uuid import uuid4

from app.services.skiptrace_service import skiptrace_case_owner, skiptrace_property_owner


def test_skiptrace_property_owner_batchdata():
    result = skiptrace_property_owner(address="123 Main St", provider="batchdata")
    assert "owner_name" in result
    assert isinstance(result.get("phones"), list)


def test_skiptrace_case_owner_normalized():
    case_id = uuid4()
    result = skiptrace_case_owner(case_id=case_id, address="123 Main St", provider="propstream")
    assert result["case_id"] == str(case_id)
    assert isinstance(result.get("emails"), list)
