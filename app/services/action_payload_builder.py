from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException


@dataclass(frozen=True)
class ActionContract:
    required_fields: tuple[str, ...] = ()
    optional_fields: tuple[str, ...] = ()
    defaults: dict[str, Any] | None = None
    context_fields: dict[str, str] | None = None


@dataclass(frozen=True)
class ActionExecutionContext:
    actor_id: UUID | None = None
    case_id: UUID | None = None
    profile_id: UUID | None = None
    state: str | None = None


ACTION_CONTRACTS: dict[str, ActionContract] = {
    "create_case_from_lead": ActionContract(
        required_fields=("lead_id", "actor_id"),
        optional_fields=("metadata",),
        context_fields={"actor_id": "actor_id"},
    ),
    "route_case_partner": ActionContract(
        required_fields=("case_id", "state", "routing_category"),
        defaults={"routing_category": "nonprofit_support", "state": "TX"},
        context_fields={"case_id": "case_id", "state": "state"},
    ),
    "portfolio_summary": ActionContract(
        required_fields=("case_id",),
        context_fields={"case_id": "case_id"},
    ),
    "analyze_property": ActionContract(
        required_fields=(
            "case_id",
            "estimated_property_value",
            "loan_balance",
            "arrears_amount",
            "foreclosure_stage",
        ),
        defaults={"foreclosure_stage": "pre_foreclosure"},
        context_fields={"case_id": "case_id"},
    ),
    "create_foreclosure_profile": ActionContract(
        required_fields=(
            "property_address",
            "estimated_property_value",
            "loan_balance",
            "arrears_amount",
            "foreclosure_stage",
        ),
        defaults={"foreclosure_stage": "pre_foreclosure"},
    ),
    "create_worker_profile": ActionContract(
        required_fields=("actor_id", "profession", "state", "city"),
        defaults={"first_time_homebuyer": "true"},
        context_fields={"actor_id": "actor_id", "state": "state"},
    ),
    "discover_housing_programs": ActionContract(
        required_fields=("profile_id",),
        context_fields={"profile_id": "profile_id"},
    ),
    "generate_homebuyer_action_plan": ActionContract(
        required_fields=("profile_id",),
        context_fields={"profile_id": "profile_id"},
    ),
}


def normalize_action_name(action_name: str) -> str:
    return action_name.strip().lower().replace("-", "_")


def build_action_payload(
    action_name: str,
    payload: dict[str, Any] | None,
    *,
    context: ActionExecutionContext,
) -> dict[str, Any]:
    """Construct and validate deterministic payloads for action execution."""

    normalized = normalize_action_name(action_name)
    contract = ACTION_CONTRACTS.get(normalized)
    built = dict(payload or {})

    if not contract:
        return built

    for field, context_attr in (contract.context_fields or {}).items():
        if built.get(field) not in (None, ""):
            continue
        context_value = getattr(context, context_attr, None)
        if context_value is not None:
            built[field] = context_value

    for field, value in (contract.defaults or {}).items():
        if built.get(field) in (None, ""):
            built[field] = value

    missing = [field for field in contract.required_fields if built.get(field) in (None, "")]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "action_payload_validation_failed",
                "action": normalized,
                "missing_fields": missing,
            },
        )

    return built
