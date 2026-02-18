import json
from uuid import uuid4


def auth_headers(client, email="worker@example.com", password="secret123"):
    resp = client.post(
        "/auth/token",
        data={"username": email, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_case(client, program_key="training_sandbox") -> str:
    response = client.post(
        "/cases",
        json={
            "program_key": program_key,
            "created_by": str(uuid4()),
            "meta": {
                "contact_hash": uuid4().hex,
                "first_name": "Test",
                "zip_code": "75201",
                "source_organization": "qa",
            },
        },
    )
    response.raise_for_status()
    return response.json()["id"]


def assume_role(client, headers, role_name, case_id):
    resp = client.post(
        "/auth/assume-role",
        json={"role_name": role_name, "case_id": case_id, "duration_minutes": 30},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def upload_document(client, headers, case_id: str, doc_type="id_verification", meta=None):
    meta = meta or {}
    return client.post(
        "/documents/",
        data={"case_id": case_id, "doc_type": doc_type, "meta": json.dumps(meta)},
        files={"file": ("evidence.txt", b"sample", "text/plain")},
        headers=headers,
    )


def queue_referral(client, headers, case_id: str, partner_id: str):
    return client.post(f"/cases/{case_id}/referral/", json={"partner_id": partner_id}, headers=headers)


def grant_consent(client, headers, case_id: str, scope):
    return client.post("/consent/", json={"case_id": case_id, "scope": scope}, headers=headers)


def ai_dryrun(client, headers, case_id: str):
    return client.post(
        "/ai/dryrun",
        json={"case_id": case_id, "prompt": "Summarize", "role": "assistive", "policy_rule_id": "r1"},
        headers=headers,
    )
