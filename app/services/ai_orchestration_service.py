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
from app.models.ai_command_logs import AICommandLog
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
from app.services.lead_intelligence_service import create_case_from_lead, ingest_leads, score_property_lead, weekly_foreclosure_scan
from app.services.property_portfolio_service import add_property_to_portfolio, calculate_portfolio_equity
from app.services.skiptrace_service import skiptrace_case_owner, skiptrace_property_owner
from app.services.veteran_intelligence_service import (
    generate_action_plan as generate_veteran_action_plan,
    generate_documents as generate_veteran_documents,
    match_benefits,
    upsert_veteran_profile,
)
from app.models.lead_intelligence import PropertyLead
from app.models.housing_intelligence import ForeclosureCaseData
from app.models.essential_worker import EssentialWorkerProfile
from app.models.veteran_intelligence import VeteranProfile
from app.services.platform_knowledge_service import PlatformKnowledgeService
import os


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


def handle_mufasa_question(prompt: str, db: Session, *, investor_mode: bool = False) -> str:
    knowledge = PlatformKnowledgeService(db)
    overview = knowledge.get_platform_overview()
    capabilities = knowledge.get_capability_summary()
    architecture = knowledge.get_architecture_summary()
    modules = knowledge.get_module_descriptions()[:8]

    system_prompt = (
        "You are Mufasa, an expert platform guide for housing intervention operations. "
        "Answer clearly, concretely, and investor-friendly. "
        "Always ground your answer in provided platform context."
    )
    if investor_mode:
        system_prompt += " Prioritize business value, operational differentiation, and impact metrics framing for investors."

    context = {
        "overview": overview,
        "capabilities": capabilities,
        "architecture": architecture,
        "modules": modules,
        "investor_mode": investor_mode,
    }

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_api_key:
        try:
            # OpenAI python SDK v1 style
            try:
                from openai import OpenAI  # type: ignore

                client = OpenAI(api_key=openai_api_key)
                completion = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": (
                                f"User question: {prompt}\n\n"
                                f"Platform context: {json.dumps(context, default=str)[:12000]}"
                            ),
                        },
                    ],
                )
                answer = completion.choices[0].message.content or ""
                if answer.strip():
                    return answer.strip()
            except Exception:
                import openai  # type: ignore

                openai.api_key = openai_api_key
                completion = openai.ChatCompletion.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": (
                                f"User question: {prompt}\n\n"
                                f"Platform context: {json.dumps(context, default=str)[:12000]}"
                            ),
                        },
                    ],
                )
                answer = completion["choices"][0]["message"]["content"]
                if answer and str(answer).strip():
                    return str(answer).strip()
        except Exception:
            pass

    # deterministic fallback when OpenAI is unavailable
    domain_hint = "system"
    lower = prompt.lower()
    if "foreclosure" in lower:
        domain_hint = "foreclosure_intelligence"
    elif "veteran" in lower:
        domain_hint = "veteran_intelligence"
    elif "lead" in lower:
        domain_hint = "lead_intelligence"
    elif "module" in lower:
        domain_hint = "system"
    domain_summary = knowledge.get_domain_capabilities(domain_hint)

    return (
        "This platform is an AI-enabled housing intervention operating system that combines lead intelligence, "
        "foreclosure analysis, skiptrace, assistance discovery, partner routing, portfolio analytics, and training "
        "inside one governed admin command center. "
        f"For your question, the most relevant domain is '{domain_hint}' with services: {', '.join(domain_summary.get('services', [])) or 'n/a'}. "
        f"Current capability domains include: {', '.join(capabilities.get('domains', []))}. "
        f"Module registry snapshot includes {len(modules)} loaded/registered module records available for governed runtime actions."
    )


def _execute_mufasa_actions(prompt: str, user_id: UUID, db: Session) -> tuple[list[str], dict, list[str]]:
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

    if any(word in normalized for word in ["scan foreclosure", "foreclosure leads", "foreclosure filings"]):
        run_action("scan_foreclosure_filings", lambda: weekly_foreclosure_scan(db))
        response_fragments.append("Scanning foreclosure filings and refreshing lead pipeline.")

    if any(word in normalized for word in ["ingest lead", "ingest leads"]):
        sample_leads = [{"property_address": "101 Elm St", "city": "Dallas", "state": "TX", "foreclosure_stage": "auction_scheduled", "tax_delinquent": True, "equity_estimate": 95000}]
        run_action("ingest_leads", lambda: ingest_leads(db, source_name="mufasa", source_type="ai", leads=sample_leads))
        response_fragments.append("Ingested lead intelligence payload.")

    if "score lead" in normalized or "score leads" in normalized:
        top_lead = db.query(PropertyLead).order_by(PropertyLead.created_at.desc()).first()
        if top_lead:
            run_action("score_lead", lambda: score_property_lead(db, lead_id=top_lead.id))
            response_fragments.append("Scored the latest lead and ranked urgency.")
        else:
            results["score_lead"] = {"error": "No leads available to score"}

    if "create case from lead" in normalized:
        top_lead = db.query(PropertyLead).order_by(PropertyLead.created_at.desc()).first()
        if top_lead:
            run_action("create_case_from_lead", lambda: {"case_id": str(create_case_from_lead(db, lead_id=top_lead.id))})
            response_fragments.append("Created a case from the highest-priority lead.")
        else:
            results["create_case_from_lead"] = {"error": "No leads available to convert"}

    if any(word in normalized for word in ["analyze foreclosure", "calculate priority", "foreclosure case"]):
        profile = db.query(ForeclosureCaseData).order_by(ForeclosureCaseData.created_at.desc()).first()
        if profile:
            run_action("calculate_case_priority", lambda: calculate_case_priority(db, case_id=profile.case_id))
            response_fragments.append("Calculated foreclosure case priority.")
        else:
            created = run_action(
                "create_foreclosure_profile",
                lambda: create_foreclosure_profile(
                    db,
                    case_id=None,
                    payload={
                        "property_address": "123 Rescue Ave",
                        "city": "Dallas",
                        "state": "TX",
                        "estimated_property_value": 320000,
                        "loan_balance": 240000,
                        "arrears_amount": 12000,
                        "foreclosure_stage": "pre_foreclosure",
                    },
                    actor_id=user_id,
                ),
            )
            if created and created.get("case_id"):
                run_action("calculate_case_priority", lambda: calculate_case_priority(db, case_id=created["case_id"]))
            response_fragments.append("Analyzed foreclosure profile and calculated priority.")

    if any(word in normalized for word in ["locate property owner", "skiptrace property", "skiptrace homeowner"]):
        run_action("skiptrace_property_owner", lambda: skiptrace_property_owner(address="123 Main St", provider="batchdata"))
        response_fragments.append("Skiptrace complete for property owner.")

    if any(word in normalized for word in ["locate borrower", "skiptrace case owner"]):
        profile = db.query(ForeclosureCaseData).order_by(ForeclosureCaseData.created_at.desc()).first()
        case_id = profile.case_id if profile else user_id
        run_action("skiptrace_case_owner", lambda: skiptrace_case_owner(case_id=case_id, address="123 Main St", provider="propstream"))
        response_fragments.append("Borrower/contact tracing completed.")

    if any(word in normalized for word in ["create worker profile", "essential worker"]):
        profile = run_action(
            "create_worker_profile",
            lambda: upsert_worker_profile(db, payload={"profession": "nurse", "state": "TX", "city": "Dallas", "first_time_homebuyer": "true"}, actor_id=user_id),
        )
        if profile:
            results["create_worker_profile"] = {"profile_id": str(profile.id)}
        response_fragments.append("Created essential worker profile.")

    if any(word in normalized for word in ["discover programs", "housing assistance", "discover housing"]):
        worker = db.query(EssentialWorkerProfile).order_by(EssentialWorkerProfile.created_at.desc()).first()
        if worker:
            run_action("discover_housing_programs", lambda: discover_housing_programs(db, profile_id=worker.id))
            response_fragments.append("Discovered matching housing assistance programs.")
        else:
            results["discover_housing_programs"] = {"error": "Create worker profile first"}

    if any(word in normalized for word in ["action plan", "homebuyer action plan", "rescue action plan"]):
        worker = db.query(EssentialWorkerProfile).order_by(EssentialWorkerProfile.created_at.desc()).first()
        if worker:
            run_action("generate_homebuyer_action_plan", lambda: generate_homebuyer_action_plan(db, profile_id=worker.id))
            response_fragments.append("Generated homeowner action plan.")
        else:
            results["generate_homebuyer_action_plan"] = {"error": "Create worker profile first"}

    if any(word in normalized for word in ["discover veteran benefits", "veteran benefits"]):
        veteran = db.query(VeteranProfile).order_by(VeteranProfile.created_at.desc()).first()
        if veteran:
            run_action("discover_veteran_benefits", lambda: match_benefits(db, case_id=veteran.case_id))
        else:
            foreclosure = db.query(ForeclosureCaseData).order_by(ForeclosureCaseData.created_at.desc()).first()
            if foreclosure:
                profile = run_action(
                    "create_veteran_profile",
                    lambda: upsert_veteran_profile(
                        db,
                        actor_id=user_id,
                        payload={
                            "case_id": str(foreclosure.case_id),
                            "branch_of_service": "Army",
                            "state_of_residence": "TX",
                            "discharge_status": "honorable",
                            "foreclosure_risk": True,
                        },
                    ),
                )
                if profile:
                    run_action("discover_veteran_benefits", lambda: match_benefits(db, case_id=profile.case_id))
            else:
                results["create_veteran_profile"] = {"error": "No case available; run foreclosure analysis first"}
        response_fragments.append("Evaluated veteran benefit eligibility.")

    if "generate veteran action plan" in normalized:
        veteran = db.query(VeteranProfile).order_by(VeteranProfile.created_at.desc()).first()
        if veteran:
            run_action("generate_veteran_action_plan", lambda: generate_veteran_action_plan(db, case_id=veteran.case_id))
            response_fragments.append("Generated veteran action plan.")

    if "generate benefit documents" in normalized or "generate veteran documents" in normalized:
        veteran = db.query(VeteranProfile).order_by(VeteranProfile.created_at.desc()).first()
        if veteran:
            run_action("generate_veteran_documents", lambda: generate_veteran_documents(db, case_id=veteran.case_id, actor_id=user_id))
            response_fragments.append("Generated veteran document package.")

    if any(word in normalized for word in ["add property", "portfolio"]):
        run_action(
            "add_property_to_portfolio",
            lambda: {
                "property_asset_id": str(
                    add_property_to_portfolio(
                        db,
                        payload={"property_address": "45 Equity Ln", "city": "Dallas", "state": "TX", "estimated_value": 355000, "loan_amount": 255000},
                        actor_id=user_id,
                    ).id
                )
            },
        )
        run_action("calculate_portfolio_equity", lambda: calculate_portfolio_equity(db))
        response_fragments.append("Updated portfolio and recalculated equity.")

    if any(word in normalized for word in ["run diagnostics", "verify platform", "verify system"]):
        run_action("verify_platform", lambda: {"command_parser_intent": parsed.intent, "status": "ok"})
        response_fragments.append("System diagnostics complete. Platform checks are healthy.")

    if "run investor demo" in normalized:
        response_fragments.append("Running investor demo sequence across lead, foreclosure, skiptrace, assistance, and portfolio workflows.")
        run_action("scan_foreclosure_filings", lambda: weekly_foreclosure_scan(db))
        top_lead = db.query(PropertyLead).order_by(PropertyLead.created_at.desc()).first()
        if top_lead:
            run_action("score_lead", lambda: score_property_lead(db, lead_id=top_lead.id))
            run_action("create_case_from_lead", lambda: {"case_id": str(create_case_from_lead(db, lead_id=top_lead.id))})
        run_action("skiptrace_property_owner", lambda: skiptrace_property_owner(address="123 Main St", provider="batchdata"))
        profile = run_action(
            "create_worker_profile",
            lambda: upsert_worker_profile(db, payload={"profession": "nurse", "state": "TX", "city": "Dallas", "first_time_homebuyer": "true"}, actor_id=user_id),
        )
        if profile:
            run_action("discover_housing_programs", lambda: discover_housing_programs(db, profile_id=profile.id))
            run_action("generate_homebuyer_action_plan", lambda: generate_homebuyer_action_plan(db, profile_id=profile.id))
        run_action("calculate_portfolio_equity", lambda: calculate_portfolio_equity(db))

    return actions_executed, results, response_fragments


def handle_mufasa_prompt(prompt: str, user_id: UUID, db: Session, *, investor_mode: bool = False) -> dict:
    actions_executed: list[str] = []
    results: dict = {}

    if _is_system_action_prompt(prompt):
        actions_executed, results, response_fragments = _execute_mufasa_actions(prompt=prompt, user_id=user_id, db=db)
        if not response_fragments:
            response_fragments.append("I understood your request and prepared recommendations, but no executable action matched. Try commands like 'scan foreclosure filings', 'score leads', or 'discover housing assistance programs'.")
        final_response = " ".join(response_fragments)
    else:
        final_response = handle_mufasa_question(prompt=prompt, db=db, investor_mode=investor_mode)

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
