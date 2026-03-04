from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException

from ai.command_parser import parse_command
from ai.operations_brain import personality_loaded
from app.models.audit_logs import AuditLog
from app.models.users import User, UserRole
from app.services.ai_orchestration_service import execute_message


def test_ai_cannot_mutate_db_directly_via_ai_module_surface(db_session):
    forbidden = ["sqlalchemy", "app.models", "Session(", ".query("]
    for file in [
        Path("ai/council_prompt.py"),
        Path("ai/operations_brain.py"),
        Path("ai/role_manager.py"),
        Path("ai/command_parser.py"),
        Path("ai/context_builder.py"),
        Path("ai/voice_interface.py"),
    ]:
        text = file.read_text()
        assert not any(token in text for token in forbidden)


def test_ai_execution_requires_confirmation(db_session):
    user = User(id=uuid4(), email=f"phase7-confirm-{uuid4().hex[:6]}@example.com", hashed_password="x", role=UserRole.admin)
    db_session.add(user)
    db_session.commit()

    with pytest.raises(HTTPException):
        execute_message(db_session, "run daily risk", confirm=False, user=user)


def test_ai_execution_creates_audit_entry(db_session):
    user = User(id=uuid4(), email=f"phase7-audit-{uuid4().hex[:6]}@example.com", hashed_password="x", role=UserRole.admin)
    db_session.add(user)
    db_session.commit()

    out = execute_message(db_session, "run daily risk", confirm=True, user=user)
    assert out["status"] == "success"
    assert out["audit_log_id"]
    assert db_session.query(AuditLog).filter(AuditLog.id == out["audit_log_id"]).count() == 1


def test_ai_idempotency_preserved_for_repeat_command(db_session):
    user = User(id=uuid4(), email=f"phase7-idem-{uuid4().hex[:6]}@example.com", hashed_password="x", role=UserRole.admin)
    db_session.add(user)
    db_session.commit()

    first = execute_message(db_session, "run daily risk", confirm=True, user=user)
    second = execute_message(db_session, "run daily risk", confirm=True, user=user)

    assert first["audit_log_id"] == second["audit_log_id"]
    assert second["state_delta"]["idempotent_replay"] is True


def test_ai_role_restriction_enforced(db_session):
    read_user = User(
        id=uuid4(),
        email=f"phase7-role-{uuid4().hex[:6]}@example.com",
        hashed_password="x",
        role=UserRole.audit_steward,
    )
    db_session.add(read_user)
    db_session.commit()

    assert parse_command("run daily risk").execution_request is True
    with pytest.raises(HTTPException):
        execute_message(db_session, "run daily risk", confirm=True, user=read_user)


def test_council_personality_loaded():
    assert personality_loaded() is True
