from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
from models import Case, ConsentRecord, AuditLog, Document, Certification, OutboxQueue, AIActivityLog

# ----------------------
# 📁 CASE HELPERS
# ----------------------

def create_case(client: TestClient, policy="default") -> str:
    """
    Create a basic case with optional policy key.
    """
    response = client.post("/cases", json={
        "participant_id": str(uuid4()),
        "program_type": "standard",
        "policy_version_id": policy
    })
    response.raise_for_status()
    return response.json()["id"]

def create_training_case(client: TestClient) -> str:
    """
    Create a case with 'training_enrollment' program_type and sandbox policy.
    """
    response = client.post("/cases", json={
        "participant_id": str(uuid4()),
        "program_type": "training_enrollment",
        "policy_version_id": "training_sandbox"
    })
    response.raise_for_status()
    return response.json()["id"]

def patch_status(client: TestClient, case_id: str, new_status: str):
    """
    Patch a case's status.
    """
    response = client.patch(f"/cases/{case_id}/status", json={"new_status": new_status})
    response.raise_for_status()
    return response

# ----------------------
# 📁 REFERRALS
# ----------------------

def queue_referral(client: TestClient, case_id: str, partner_id: str):
    """
    Queue a referral request for a given case and partner.
    """
    response = client.post(f"/cases/{case_id}/referral", json={
        "partner_id": partner_id
    })
    response.raise_for_status()
    return response

# ----------------------
# 📁 DOCUMENTS + CONSENT
# ----------------------

def upload_document(client: TestClient, case_id: str, doc_type="id_verification", meta=None):
    """
    Upload a document with optional metadata.
    """
    meta = meta or {}
    response = client.post("/documents", json={
        "case_id": case_id,
        "doc_type": doc_type,
        "meta": meta
    })
    response.raise_for_status()
    return response

def upload_taskcheck_evidence(client: TestClient, case_id: str, evidence_type: str):
    """
    Upload a document of type 'other' as taskcheck evidence.
    """
    return upload_document(client, case_id, doc_type="other", meta={
        "evidence_type": "manual_form_upload",
        "description": evidence_type
    })

def grant_ai_consent(client: TestClient, case_id: str):
    """
    Grant AI usage consent to a case.
    """
    response = client.post("/consent", json={
        "case_id": case_id,
        "granted_by_user_id": str(uuid4()),
        "scope": ["ai_use"],
    })
    response.raise_for_status()
    return response

# ----------------------
# 📁 QUIZZES + CERTS
# ----------------------

def submit_quiz(client: TestClient, case_id: str, quiz_id: str, correct=True):
    """
    Submit a quiz attempt with either correct or incorrect answer.
    """
    response = client.post(f"/cases/{case_id}/quiz", json={
        "quiz_id": quiz_id,
        "answers": {"q1": "correct" if correct else "wrong"}
    })
    response.raise_for_status()
    return response

def get_cert_for_user(db: Session, user_id: str):
    """
    Fetch certification record for a given user.
    """
    return db.query(Certification).filter(Certification.user_id == user_id).first()

# ----------------------
# 📁 AUDIT + AI LOGGING
# ----------------------

def get_audit_logs(db: Session, case_id: str):
    """
    Return all audit logs for a case.
    """
    return db.query(AuditLog).filter(AuditLog.case_id == case_id).all()

def get_audit_log_for_action(db: Session, case_id: str, action_type: str):
    """
    Return specific audit log by action type.
    """
    return db.query(AuditLog).filter(
        AuditLog.case_id == case_id,
        AuditLog.action_type == action_type
    ).first()

def get_ai_logs(db: Session, case_id: str):
    """
    Fetch AI logs for a case.
    """
    return db.query(AIActivityLog).filter(AIActivityLog.case_id == case_id).all()

# ----------------------
# 📁 OUTBOX
# ----------------------

def create_outbox_entry(db: Session, attempts=0):
    """
    Create a simulated outbox queue job.
    """
    entry = OutboxQueue(
        id=str(uuid4()),
        case_id=str(uuid4()),
        payload={"sample": "data"},
        dedupe_key="unique-key",
        attempts=attempts,
        created_at=datetime.utcnow()
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def simulate_failure(entry: OutboxQueue):
    """
    Simulate failure in outbox entry.
    """
    entry.attempts += 1
    entry.failed = True
    return entry

def run_worker():
    """
    Stub for running Celery/worker task.
    """
    print("Running outbox worker... (stub)")

def get_outbox_by_id(db: Session, id: str):
    """
    Get outbox queue entry by ID.
    """
    return db.query(OutboxQueue).filter(OutboxQueue.id == id).first()
