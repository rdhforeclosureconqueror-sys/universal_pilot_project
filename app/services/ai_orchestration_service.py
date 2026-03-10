from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ai.command_parser import parse_command
from ai.context_builder import build_context
from ai.operations_brain import build_advisory
from ai.role_manager import AIRole, authorize, user_ai_role
from ai.voice_interface import synthesize_audio, transcribe_audio
from app.models.audit_logs import AuditLog
from app.models.users import User
from internal.ai_gateway import execute_gateway_action
from app.services.veteran_intelligence_service import get_advisory
import re
from uuid import UUID


def _state_hash(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def advisory_message(db: Session, message: str) -> dict:
    parsed = parse_command(message)
    context = build_context(db)

    if parsed.intent == "veteran_benefit_advisory":
        case_match = re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", message)
        if case_match:
            try:
                advisory = get_advisory(db, case_id=UUID(case_match.group(0)), question=message)
                response = advisory["answer"]
            except Exception:
                response = "Veteran advisory is available. Please provide a valid case UUID tied to a veteran profile for precise eligibility results."
        else:
            response = "To answer veteran eligibility questions precisely, include the case UUID linked to the veteran profile."
    else:
        response = build_advisory(message, parsed, context)

    return {
        "advisory_response": response,
        "execution_request": parsed.execution_request,
        "parsed_intent": parsed.intent,
    }


def execute_message(db: Session, message: str, confirm: bool, user: User) -> dict:
    parsed = parse_command(message)
    actor_role = user_ai_role(user)

    if parsed.intent == "structure_plan":
        return {
            "status": "success",
            "audit_log_id": None,
            "state_delta": {"note": "STRUCTURE role returns migration plan only; no direct execution."},
        }

    if parsed.execution_request and not confirm:
        raise HTTPException(status_code=400, detail="Execution requires confirm=true")

    if not authorize(parsed.required_role, actor_role):
        db.add(
            AuditLog(
                case_id=None,
                actor_id=user.id,
                actor_is_ai=False,
                action_type="ai_denied",
                reason_code=f"ai_denied_{parsed.intent}",
                before_state={"requested_role": parsed.required_role.value, "provided_role": actor_role.value},
                after_state={"authorized": False},
                policy_version_id=None,
            )
        )
        db.commit()
        raise HTTPException(status_code=403, detail="AI role authorization denied")

    idempotency_key = hashlib.sha256(f"{user.id}:{parsed.intent}:{json.dumps(parsed.params, sort_keys=True)}".encode("utf-8")).hexdigest()
    existing = (
        db.query(AuditLog)
        .filter(
            AuditLog.action_type == "ai_initiated",
            AuditLog.reason_code == f"ai_exec_{idempotency_key}",
        )
        .first()
    )
    if existing:
        return {
            "status": "success",
            "audit_log_id": str(existing.id),
            "state_delta": {"idempotent_replay": True},
        }

    pre_state = {
        "intent": parsed.intent,
        "params": parsed.params,
        "authorized_by": "owner",
        "ai_role_used": actor_role.value,
    }
    previous_state_hash = _state_hash(pre_state)
    gateway_result = execute_gateway_action(db, parsed.intent, parsed.params)
    post_state = {
        **pre_state,
        "gateway_result": gateway_result,
        "new_state_hash": None,
    }
    new_state_hash = _state_hash(post_state)
    post_state["new_state_hash"] = new_state_hash

    log = AuditLog(
        case_id=None,
        actor_id=user.id,
        actor_is_ai=False,
        action_type="ai_initiated",
        reason_code=f"ai_exec_{idempotency_key}",
        before_state={**pre_state, "previous_state_hash": previous_state_hash},
        after_state=post_state,
        policy_version_id=None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return {
        "status": "success",
        "audit_log_id": str(log.id),
        "state_delta": {
            "intent": parsed.intent,
            "authorized_by": "owner",
            "ai_role_used": actor_role.value,
            "previous_state_hash": previous_state_hash,
            "new_state_hash": new_state_hash,
            "idempotent_replay": False,
            "result": gateway_result,
        },
    }


def process_voice(db: Session, audio_bytes: bytes, confirm_phrase: str | None, user: User) -> dict:
    transcript = transcribe_audio(audio_bytes)
    advisory = advisory_message(db, transcript)
    execution_allowed = bool(confirm_phrase and "confirm" in confirm_phrase.lower())
    execution = None
    if advisory["execution_request"] and execution_allowed:
        execution = execute_message(db, transcript, confirm=True, user=user)
    elif advisory["execution_request"] and not execution_allowed:
        execution = {"status": "blocked", "reason": "confirmation_phrase_required"}

    response_text = advisory["advisory_response"]
    return {
        "transcript": transcript,
        "advisory": advisory,
        "execution": execution,
        "audio_response_b64": synthesize_audio(response_text).decode("utf-8", errors="ignore"),
    }
