from datetime import datetime, timedelta, timezone
from uuid import uuid4


def test_get_cases_lists_newly_created_case(client, seeded_policy):
    payload = {
        "program_key": "training_sandbox",
        "created_by": str(uuid4()),
        "meta": {
            "contact_hash": uuid4().hex,
            "first_name": "Case",
            "zip_code": "75201",
            "source_organization": "phase7",
        },
    }

    create_response = client.post("/cases", json=payload)
    assert create_response.status_code == 200
    created_case_id = create_response.json()["id"]

    list_response = client.get("/cases")
    assert list_response.status_code == 200
    cases = list_response.json()
    assert any(case["id"] == created_case_id for case in cases)


def test_get_cases_supports_filters(client, seeded_policy):
    now = datetime.now(timezone.utc)
    payload = {
        "program_key": "training_sandbox",
        "created_by": str(uuid4()),
        "meta": {
            "contact_hash": uuid4().hex,
            "first_name": "Filter",
            "zip_code": "75201",
            "source_organization": "phase7",
        },
    }
    create_response = client.post("/cases", json=payload)
    assert create_response.status_code == 200
    created_case_id = create_response.json()["id"]

    response = client.get(
        "/cases",
        params={
            "status": "intake_incomplete",
            "program_key": "training_sandbox",
            "created_from": (now - timedelta(minutes=5)).isoformat(),
            "created_to": (now + timedelta(minutes=5)).isoformat(),
        },
    )

    assert response.status_code == 200
    records = response.json()
    assert any(case["id"] == created_case_id for case in records)
