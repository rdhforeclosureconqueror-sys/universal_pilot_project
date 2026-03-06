from __future__ import annotations

from typing import Any, Callable
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.module_registry import ModuleRegistry
from app.models.users import User

from app.services.escalation_service import run_daily_risk_evaluation

from app.services.foreclosure_intelligence_service import (
    calculate_case_priority,
)

from app.services.property_analysis_service import (
    calculate_acquisition_score,
    calculate_equity,
    calculate_ltv,
    calculate_rescue_score,
    classify_intervention,
)

from app.services.partner_routing_service import route_case_to_partner

from app.services.property_portfolio_service import (
    add_property_to_portfolio,
    calculate_portfolio_equity,
)

from app.services.membership_service import create_membership

from app.services.veteran_intelligence_service import (
    calculate_benefit_value,
    generate_action_plan,
    generate_documents,
    get_advisory,
    match_benefits,
    partner_aggregate_report,
    update_benefit_progress,
    upsert_veteran_profile,
)

from app.services.module_registry_service import ModuleRegistryService
from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from db.session import SessionLocal, get_db


# ---------------------------------------------------
# Request Schema
# ---------------------------------------------------

class ModuleActionRequest(BaseModel):
    case_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------
# Domain Service Broker
# ---------------------------------------------------

class DomainServiceBroker:
    """Bounded dispatcher for module actions using approved domain services only."""

    def __init__(self):

        self._handlers: dict[str, tuple[str, Callable, bool]] = {

            # Escalation
            "run_daily_risk_evaluation": (
                "escalation_service",
                self._run_daily_risk_evaluation,
                False,
            ),

            # Veteran
            "upsert_veteran_profile": (
                "veteran_intelligence_service",
                self._upsert_veteran_profile,
                True,
            ),
            "scan_veteran_benefits": (
                "veteran_intelligence_service",
                self._scan_veteran_benefits,
                True,
            ),
            "generate_veteran_action_plan": (
                "veteran_intelligence_service",
                self._generate_veteran_action_plan,
                True,
            ),
            "generate_veteran_documents": (
                "document_service",
                self._generate_veteran_documents,
                True,
            ),
            "update_benefit_progress": (
                "veteran_intelligence_service",
                self._update_benefit_progress,
                True,
            ),
            "veteran_ai_advisory": (
                "veteran_intelligence_service",
                self._veteran_ai_advisory,
                True,
            ),
            "veteran_partner_aggregate_report": (
                "veteran_intelligence_service",
                self._veteran_partner_aggregate_report,
                False,
            ),
            "calculate_veteran_benefit_value": (
                "veteran_intelligence_service",
                self._calculate_veteran_benefit_value,
                True,
            ),

            # Housing Intelligence
            "calculate_case_priority": (
                "foreclosure_intelligence_service",
                self._calculate_case_priority,
                True,
            ),
            "analyze_property": (
                "property_analysis_service",
                self._analyze_property,
                True,
            ),
            "route_case_partner": (
                "partner_routing_service",
                self._route_case_partner,
                True,
            ),
            "add_property_to_portfolio": (
                "property_portfolio_service",
                self._add_property_to_portfolio,
                True,
            ),
            "portfolio_summary": (
                "property_portfolio_service",
                self._portfolio_summary,
                True,
            ),
            "create_membership_profile": (
                "membership_service",
                self._create_membership_profile,
                True,
            ),
        }

        self.allowed_services = {
            "activation_service",
            "admin_dashboard_service",
            "ai_orchestration_service",
            "application_service",
            "auth_service",
            "escalation_service",
            "member_dashboard_service",
            "membership_service",
            "payment_service",
            "qualification_service",
            "stability_service",
            "workflow_service",
            "document_service",
            "veteran_intelligence_service",
            "foreclosure_intelligence_service",
            "property_analysis_service",
            "partner_routing_service",
            "property_portfolio_service",
        }

    # ---------------------------------------------------
    # Validation
    # ---------------------------------------------------

    def validate_required_services(self, required_services: list[str]):

        unknown = sorted(set(required_services) - self.allowed_services)

        if unknown:
            return False, f"unknown required services: {', '.join(unknown)}"

        return True, "required services are valid"

    # ---------------------------------------------------
    # Execution
    # ---------------------------------------------------

    def execute_action(
        self,
        db: Session,
        *,
        module: ModuleRegistry,
        action_name: str,
        payload: dict[str, Any],
        actor_id: UUID | None = None,
    ):

        if action_name not in (module.allowed_actions or []):
            raise HTTPException(
                status_code=403,
                detail=f"Action '{action_name}' not allowed for module",
            )

        mapped = self._handlers.get(action_name)

        if not mapped:
            raise HTTPException(
                status_code=501,
                detail=f"No safe domain-service mapping for action '{action_name}'",
            )

        service_name, handler, requires_actor = mapped

        if service_name not in (module.required_services or []):
            raise HTTPException(
                status_code=400,
                detail=f"Action '{action_name}' requires service '{service_name}' declared in required_services",
            )

        return handler(db, payload, requires_actor, actor_id)

    # ---------------------------------------------------
    # Escalation
    # ---------------------------------------------------

    @staticmethod
    def _run_daily_risk_evaluation(db: Session, payload: dict[str, Any], *_):
        return run_daily_risk_evaluation(db)
staticmethod
    def _veteran_ai_advisory(db: Session, payload: dict[str, Any], *_):
        case_id = _payload_uuid(payload, "case_id")
        return get_advisory(
            db,
            case_id=case_id,
            question=payload.get("question", ""),
        )

    @staticmethod
    def _veteran_partner_aggregate_report(db: Session, payload: dict[str, Any], *_):
        return {
            "rows": partner_aggregate_report(
                db,
                state_of_residence=payload.get("state_of_residence"),
            )
        }

    @staticmethod
    def _calculate_veteran_benefit_value(db: Session, payload: dict[str, Any], *_):
        case_id = _payload_uuid(payload, "case_id")
        return calculate_benefit_value(db, case_id=case_id)

    # ---------------------------------------------------
    # Housing OS
    # ---------------------------------------------------

    @staticmethod
    def _calculate_case_priority(db: Session, payload: dict[str, Any], *_):
        case_id = _payload_uuid(payload, "case_id")
        return calculate_case_priority(db, case_id=case_id)

    @staticmethod
    def _analyze_property(db: Session, payload: dict[str, Any], *_):

        estimated_value = float(payload.get("estimated_property_value", 0))
        loan_balance = float(payload.get("loan_balance", 0))
        arrears = float(payload.get("arrears_amount", 0))
        income = float(payload.get("homeowner_income", 0))
        stage = str(payload.get("foreclosure_stage", "pre_foreclosure"))

        equity = calculate_equity(
            estimated_property_value=estimated_value,
            loan_balance=loan_balance,
        )

        ltv = calculate_ltv(
            loan_balance=loan_balance,
            estimated_property_value=estimated_value,
        )

        rescue_score = calculate_rescue_score(
            arrears_amount=arrears,
            homeowner_income=income,
            foreclosure_stage=stage,
        )

        acquisition_score = calculate_acquisition_score(
            equity=equity,
            ltv=ltv,
            foreclosure_stage=stage,
        )

        classification = classify_intervention(
            rescue_score=rescue_score,
            acquisition_score=acquisition_score,
            ltv=ltv,
        )

        return {
            "equity": equity,
            "ltv": ltv,
            "rescue_score": rescue_score,
            "acquisition_score": acquisition_score,
            "classification": classification,
        }

    @staticmethod
    def _route_case_partner(db: Session, payload: dict[str, Any], _, actor_id: UUID | None):

        referral = route_case_to_partner(
            db,
            case_id=_payload_uuid(payload, "case_id"),
            state=str(payload.get("state", "")),
            routing_category=str(payload.get("routing_category", "nonprofit_support")),
            actor_id=actor_id,
        )

        return {
            "partner_referral_id": str(referral.id),
            "status": referral.status,
        }

    @staticmethod
    def _add_property_to_portfolio(db: Session, payload: dict[str, Any], _, actor_id: UUID | None):

        asset = add_property_to_portfolio(
            db,
            payload=payload,
            actor_id=actor_id,
        )

        return {"property_asset_id": str(asset.id)}

    @staticmethod
    def _portfolio_summary(db: Session, payload: dict[str, Any], *_):
        del payload
        return calculate_portfolio_equity(db)

    @staticmethod
    def _create_membership_profile(db: Session, payload: dict[str, Any], _, actor_id: UUID | None):

        profile = create_membership(
            db,
            user_id=_payload_uuid(payload, "user_id"),
            case_id=_payload_uuid(payload, "case_id"),
            membership_type=str(payload.get("membership_type", "cooperative")),
            actor_id=actor_id,
        )

        return {"membership_profile_id": str(profile.id)}