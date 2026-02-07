import os
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api.main import app
from auth.auth_handler import hash_password
from db.session import SessionLocal, get_db
from models.policy_versions import PolicyVersion
from models.users import User, UserRole


@pytest.fixture(scope="function")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seeded_user(db_session):
    user = User(
        id=uuid4(),
        email="worker@example.com",
        hashed_password=hash_password("secret123"),
        role=UserRole.case_worker,
        full_name="Case Worker",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def seeded_policy(db_session):
    policy = PolicyVersion(
        id=uuid4(),
        program_key="training_sandbox",
        version_tag=f"test_{uuid4().hex[:8]}",
        is_active=True,
        config_json={
            "custom_fields": ["contact_hash", "first_name", "zip_code", "source_organization"],
            "review_required": True,
            "role_eligibility": {
                "case_worker": ["case_worker", "referral_coordinator", "ai_policy_chair"],
            },
            "permissions": {
                "actions": {
                    "documents.upload": ["case_worker"],
                    "documents.read": ["case_worker"],
                    "documents.list": ["case_worker"],
                    "consent.grant": ["case_worker"],
                    "consent.revoke": ["case_worker"],
                    "referral.queue": ["referral_coordinator", "case_worker"],
                    "training.quiz_attempt": ["case_worker"],
                    "ai.dryrun": ["ai_policy_chair", "case_worker"],
                }
            },
            "required_quizzes": [
                {
                    "quiz_key": "quiz_policy_versions",
                    "min_pass_score": 0.5,
                    "questions": [
                        {"prompt": "q1", "correct_answer": "a1"},
                    ],
                }
            ],
            "ai_settings": {
                "ai_kill_switch_enabled": False,
                "disable_assistive": False,
                "disable_advisory": False,
                "disable_automated": False,
            },
        },
    )
    db_session.add(policy)
    db_session.commit()
    return policy
