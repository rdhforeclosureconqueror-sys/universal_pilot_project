from __future__ import annotations

import hashlib
import json
import os
import re
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ai.command_parser import parse_command
from ai.context_builder import build_context
from ai.operations_brain import build_advisory
from ai.role_manager import AIRole, authorize, user_ai_role
from ai.voice_interface import synthesize_audio, transcribe_audio

from app.models.audit_logs import AuditLog
from app.models.users import User
from app.models.ai_command_logs import AICommandLog

from internal.ai_gateway import execute_gateway_action

from app.services.veteran_intelligence_service import (
    get_advisory,
    generate_action_plan as generate_veteran_action_plan,
    generate_documents as generate_veteran_documents,
    match_benefits,
    upsert_veteran_profile,
)

from app.services.essential_worker_housing_service import (
    discover_housing_programs,
    generate_homebuyer_action_plan,
    upsert_worker_profile,
)

from app.services.foreclosure_intelligence_service import (
    calculate_case_priority,
    create_foreclosure_profile,
)

from app.services.lead_intelligence_service import (
    create_case_from_lead,
    ingest_leads,
    score_property_lead,
    weekly_foreclosure_scan,
)

from app.services.property_portfolio_service import (
    add_property_to_portfolio,
    calculate_portfolio_equity,
)

from app.services.skiptrace_service import (
    skiptrace_case_owner,
    skiptrace_property_owner,
)

from app.services.platform_knowledge_service import PlatformKnowledgeService

from app.models.lead_intelligence import PropertyLead
from app.models.housing_intelligence import ForeclosureCaseData
from app.models.essential_worker import EssentialWorkerProfile
from app.models.veteran_intelligence import VeteranProfile


def advisory_message(db: Session, message: str) -> dict:
    parsed = parse_command(message)
    context = build_context(db)

    if parsed.intent == "veteran_benefit_advisory":
        case_match = re.search(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            message,
        )

        if case_match:
            try:
                advisory = get_advisory(
                    db,
                    case_id=UUID(case_match.group(0)),
                    question=message,
                )
                response = advisory["answer"]
            except Exception:
                response = (
                    "Veteran advisory is available. Provide a valid case UUID."
                )
        else:
            response = (
                "Include the case UUID linked to the veteran profile."
            )
    else:
        response = build_advisory(message, parsed, context)

    return {
        "advisory_response": response,
        "execution_request": parsed.execution_request,
        "parsed_intent": parsed.intent,
    }


def process_voice(
    db: Session,
    audio_bytes: bytes,
    confirm_phrase: str | None,
    user: User,
) -> dict:

    transcript = transcribe_audio(audio_bytes)

    advisory = advisory_message(db, transcript)

    execution_allowed = bool(
        confirm_phrase and "confirm" in confirm_phrase.lower()
    )

    execution = None

    if advisory["execution_request"] and execution_allowed:
        execution = {"status": "approved"}
    elif advisory["execution_request"]:
        execution = {
            "status": "blocked",
            "reason": "confirmation_phrase_required",
        }

    response_text = advisory["advisory_response"]

    return {
        "transcript": transcript,
        "advisory": advisory,
        "execution": execution,
        "audio_response_b64": synthesize_audio(response_text).decode(
            "utf-8",
            errors="ignore",
        ),
    }


def handle_mufasa_question(
    prompt: str,
    db: Session,
    *,
    investor_mode: bool = False,
) -> str:

    knowledge = PlatformKnowledgeService(db)

    overview = knowledge.get_platform_overview()

    capabilities = knowledge.get_capability_summary()

    modules = knowledge.get_module_descriptions()[:8]

    if investor_mode:
        return (
            "This platform is an AI-enabled housing intervention operating system "
            "designed for foreclosure prevention, lead intelligence, assistance discovery, "
            "partner routing, and portfolio analytics."
        )

    return (
        f"Platform overview: {overview}. "
        f"Capability domains: {', '.join(capabilities.get('domains', []))}. "
        f"Active modules loaded: {len(modules)}."
    )


def handle_mufasa_prompt(
    prompt: str,
    user_id: UUID,
    db: Session,
    *,
    investor_mode: bool = False,
) -> dict:

    response = handle_mufasa_question(
        prompt=prompt,
        db=db,
        investor_mode=investor_mode,
    )

    db.add(
        AICommandLog(
            user_id=user_id,
            message=prompt,
            ai_response=response,
            actions_triggered=[],
            results={},
        )
    )

    db.commit()

    return {
        "response": response,
        "actions_executed": [],
        "results": {},
    }