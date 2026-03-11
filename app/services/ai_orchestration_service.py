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
from ai.role_manager import authorize, user_ai_role
from ai.voice_interface import synthesize_audio, transcribe_audio

from app.models.audit_logs import AuditLog
from app.models.users import User
from internal.ai_gateway import execute_gateway_action

from app.services.veteran_intelligence_service import get_advisory
from app.services.veteran_intelligence_service import (
    generate_action_plan as generate_veteran_action_plan,
    generate_documents as generate_veteran_documents,
    match_benefits,
    upsert_veteran_profile,
)

from app.models.ai_command_logs import AICommandLog
from app.models.lead_intelligence import PropertyLead
from app.models.housing_intelligence import ForeclosureCaseData
from app.models.essential_worker import EssentialWorkerProfile
from app.models.veteran_intelligence import VeteranProfile

from app.services.platform_knowledge_service import PlatformKnowledgeService
from app.services.essential_worker_housing_service import (
    discover_housing_programs,
    generate_homebuyer_action_plan,
    upsert_worker_profile,
)
from app.services.foreclosure_intelligence_service import (
    calculate_case_priority,
    create_foreclosure_profile,
)
from app.services.impact_analytics_service import get_housing_summary
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


def _state_hash(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def advisory_message(db: Session, message: str) -> dict:
    parsed = parse_command(message)
    context = build_context(db)

    if parsed.intent == "veteran_benefit_advisory":

        case_match = re.search(
            r"[0-9a-fA-F\-]{36}",
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
                    "Veteran advisory is available. Provide a valid case UUID tied "
                    "to a veteran profile for precise eligibility results."
                )

        else:
            response = (
                "To answer veteran eligibility questions precisely, include the case UUID "
                "linked to the veteran profile."
            )

    else:
        response = build_advisory(message, parsed, context)

    return {
        "advisory_response": response,
        "execution_request": parsed.execution_request,
        "parsed_intent": parsed.intent,
    }


def _is_system_action_prompt(prompt: str) -> bool:

    text = prompt.lower().strip()

    action_keywords = [
        "scan",
        "ingest",
        "score",
        "create case",
        "analyze",
        "calculate",
        "skiptrace",
        "discover programs",
        "action plan",
        "generate veteran",
        "add property",
        "verify platform",
        "run diagnostics",
        "run investor demo",
    ]

    return any(k in text for k in action_keywords)


def handle_mufasa_question(
    prompt: str,
    db: Session,
    *,
    investor_mode: bool = False,
) -> str:

    knowledge = PlatformKnowledgeService(db)

    overview = knowledge.get_platform_overview()
    capabilities = knowledge.get_capability_summary()
    architecture = knowledge.get_architecture_summary()
    modules = knowledge.get_module_descriptions()[:8]

    system_prompt = (
        "You are Mufasa, an expert platform guide for housing intervention operations. "
        "Answer clearly using the provided platform context."
    )

    if investor_mode:
        system_prompt += (
            " Emphasize operational leverage, impact scale, and investor differentiation."
        )

    context = {
        "overview": overview,
        "capabilities": capabilities,
        "architecture": architecture,
        "modules": modules,
        "investor_mode": investor_mode,
    }

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if api_key:

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)

            completion = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nPlatform Context:\n{json.dumps(context, default=str)[:12000]}",
                    },
                ],
            )

            answer = completion.choices[0].message.content

            if answer:
                return answer.strip()

        except Exception:
            pass

    lower = prompt.lower()
    domain_hint = "system"

    if "foreclosure" in lower:
        domain_hint = "foreclosure_intelligence"

    elif "veteran" in lower:
        domain_hint = "veteran_intelligence"

    elif "lead" in lower:
        domain_hint = "lead_intelligence"

    domain_summary = knowledge.get_domain_capabilities(domain_hint)

    return (
        "This platform is an AI-enabled housing intervention operating system "
        "combining lead intelligence, foreclosure analysis, assistance discovery, "
        "partner routing, portfolio analytics, and training inside one governed "
        "command center. "
        f"Relevant domain: {domain_hint}. "
        f"Services: {', '.join(domain_summary.get('services', []))}. "
        f"Capability domains: {', '.join(capabilities.get('domains', []))}. "
        f"Registered modules: {len(modules)}."
    )


def _execute_mufasa_actions(
    prompt: str,
    user_id: UUID,
    db: Session,
):

    parsed = parse_command(prompt)
    normalized = prompt.lower().strip()

    actions_executed: list[str] = []
    results: dict = {}
    response_fragments: list[str] = []

    def run_action(name: str, fn):

        try:
            result = fn()
            actions_executed.append(name)
            results[name] = result
            return result

        except Exception as exc:
            actions_executed.append(name)
            results[name] = {"error": str(exc)}
            return None

    if "scan foreclosure" in normalized:

        run_action(
            "scan_foreclosure_filings",
            lambda: weekly_foreclosure_scan(db),
        )

        response_fragments.append("Scanning foreclosure filings.")

    if "run investor demo" in normalized:

        response_fragments.append(
            "Running investor demo across lead, foreclosure, skiptrace and portfolio workflows."
        )

        run_action(
            "scan_foreclosure_filings",
            lambda: weekly_foreclosure_scan(db),
        )

        run_action(
            "calculate_portfolio_equity",
            lambda: calculate_portfolio_equity(db),
        )

    return actions_executed, results, response_fragments


def handle_mufasa_prompt(
    prompt: str,
    user_id: UUID,
    db: Session,
    *,
    investor_mode: bool = False,
) -> dict:

    actions_executed: list[str] = []
    results: dict = {}

    if _is_system_action_prompt(prompt):

        actions_executed, results, response_fragments = _execute_mufasa_actions(
            prompt=prompt,
            user_id=user_id,
            db=db,
        )

        if not response_fragments:

            response_fragments.append(
                "I understood the request but no executable action matched."
            )

        final_response = " ".join(response_fragments)

    else:

        final_response = handle_mufasa_question(
            prompt=prompt,
            db=db,
            investor_mode=investor_mode,
        )

    db.add(
        AICommandLog(
            user_id=user_id,
            message=prompt,
            ai_response=final_response,
            actions_triggered=actions_executed,
            results=results,
        )
    )

    db.commit()

    return {
        "response": final_response,
        "actions_executed": actions_executed,
        "results": results,
    }
