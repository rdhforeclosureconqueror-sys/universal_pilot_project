from __future__ import annotations

from typing import Any, Callable
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.module_registry import ModuleRegistry
from app.models.users import User

from app.services.escalation_service import run_daily_risk_evaluation
from app.services.foreclosure_intelligence_service import calculate_case_priority
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
# Domain Broker
# ---------------------------------------------------

class DomainServiceBroker:

    def __init__(self):

        self._handlers: dict[str, tuple[str, Callable, bool]] = {

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

            # Housing OS
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

    def execute_action(
        self,
        db: Session,
        *,
        module: ModuleRegistry,
        action_name: str,
        payload: dict[str, Any],
        actor_id: UUID | None = None,
    ):

        mapped = self._handlers.get(action_name)

        if not mapped:
            raise HTTPException(status_code=404, detail="Action not supported")

        _, handler, requires_actor = mapped

        return handler(db, payload, requires_actor, actor_id)

    # ---------------------------------------------------
    # Core
    # ---------------------------------------------------

    @staticmethod
    def _run_daily_risk_evaluation(db: Session, payload: dict[str, Any], *_):
        return run_daily_risk_evaluation(db)

    # ---------------------------------------------------
    # Veteran
    # ---------------------------------------------------

    @staticmethod
    def _upsert_veteran_profile(db: Session, payload, _, actor_id):
        profile = upsert_veteran_profile(db, actor_id=actor_id, payload=payload)
        return {"case_id": str(profile.case_id)}

    @staticmethod
    def _scan_veteran_benefits(db, payload, *_):
        return match_benefits(db, _payload_uuid(payload, "case_id"))

    @staticmethod
    def _generate_veteran_action_plan(db, payload, *_):
        return generate_action_plan(db, _payload_uuid(payload, "case_id"))

    @staticmethod
    def _generate_veteran_documents(db, payload, _, actor_id):
        return generate_documents(db, _payload_uuid(payload, "case_id"), actor_id)

    @staticmethod
    def _update_benefit_progress(db, payload, _, actor_id):
        return update_benefit_progress(
            db,
            case_id=_payload_uuid(payload, "case_id"),
            benefit_name=payload.get("benefit_name"),
            status=payload.get("status"),
            actor_id=actor_id,
        )

    @staticmethod
    def _veteran_ai_advisory(db, payload, *_):
        return get_advisory(
            db,
            _payload_uuid(payload, "case_id"),
            payload.get("question"),
        )

    @staticmethod
    def _veteran_partner_aggregate_report(db, payload, *_):
        return {"rows": partner_aggregate_report(db, payload.get("state_of_residence"))}

    @staticmethod
    def _calculate_veteran_benefit_value(db, payload, *_):
        return calculate_benefit_value(db, _payload_uuid(payload, "case_id"))

    # ---------------------------------------------------
    # Housing OS
    # ---------------------------------------------------

    @staticmethod
    def _calculate_case_priority(db, payload, *_):
        return calculate_case_priority(db, _payload_uuid(payload, "case_id"))

    @staticmethod
    def _analyze_property(db, payload, *_):

        equity = calculate_equity(
            float(payload.get("estimated_property_value", 0)),
            float(payload.get("loan_balance", 0)),
        )

        ltv = calculate_ltv(
            float(payload.get("loan_balance", 0)),
            float(payload.get("estimated_property_value", 0)),
        )

        rescue_score = calculate_rescue_score(
            float(payload.get("arrears_amount", 0)),
            float(payload.get("homeowner_income", 0)),
            payload.get("foreclosure_stage", "pre_foreclosure"),
        )

        acquisition_score = calculate_acquisition_score(
            equity,
            ltv,
            payload.get("foreclosure_stage", "pre_foreclosure"),
        )

        return {
            "equity": equity,
            "ltv": ltv,
            "rescue_score": rescue_score,
            "acquisition_score": acquisition_score,
            "classification": classify_intervention(
                rescue_score=rescue_score,
                acquisition_score=acquisition_score,
                ltv=ltv,
            ),
        }

    @staticmethod
    def _route_case_partner(db, payload, _, actor_id):

        referral = route_case_to_partner(
            db,
            case_id=_payload_uuid(payload, "case_id"),
            state=payload.get("state"),
            routing_category=payload.get("routing_category"),
            actor_id=actor_id,
        )

        return {"partner_referral_id": str(referral.id)}

    @staticmethod
    def _add_property_to_portfolio(db, payload, _, actor_id):
        asset = add_property_to_portfolio(db, payload=payload, actor_id=actor_id)
        return {"property_asset_id": str(asset.id)}

    @staticmethod
    def _portfolio_summary(db, payload, *_):
        return calculate_portfolio_equity(db)

    @staticmethod
    def _create_membership_profile(db, payload, _, actor_id):

        profile = create_membership(
            db,
            user_id=_payload_uuid(payload, "user_id"),
            case_id=_payload_uuid(payload, "case_id"),
            membership_type=payload.get("membership_type", "cooperative"),
            actor_id=actor_id,
        )

        return {"membership_profile_id": str(profile.id)}


# ---------------------------------------------------
# Module Loader
# ---------------------------------------------------

class ModuleLoaderService:

    def __init__(self, app: FastAPI, db: Session):
        self.app = app
        self.db = db
        self.domain_broker = DomainServiceBroker()
        self.registry_service = ModuleRegistryService(db)

    def load_active_modules(self) -> int:

        modules = (
            self.db.query(ModuleRegistry)
            .filter(ModuleRegistry.is_active == True)
            .all()
        )

        loaded = 0

        for module in modules:
            self._register_router(module)
            loaded += 1

        return loaded

    def _register_router(self, module: ModuleRegistry):

        router = APIRouter(prefix=f"/modules/{module.module_name}")

        @router.post("/actions/{action_name}")
        def run_action(
            action_name: str,
            request: ModuleActionRequest,
            db: Session = Depends(get_db),
            user: User = Depends(get_current_user),
        ):

            result = self.domain_broker.execute_action(
                db,
                module=module,
                action_name=action_name,
                payload=request.payload,
                actor_id=user.id,
            )

            db.add(
                AuditLog(
                    id=uuid4(),
                    case_id=UUID(request.case_id),
                    actor_id=user.id,
                    actor_is_ai=False,
                    action_type="module_action",
                    reason_code=f"{module.module_name}:{action_name}",
                    before_state={},
                    after_state=result,
                    policy_version_id=None,
                )
            )

            db.commit()

            return {"result": result}

        self.app.include_router(router)


# ---------------------------------------------------
# Utility
# ---------------------------------------------------

def _payload_uuid(payload: dict[str, Any], field: str) -> UUID:

    value = payload.get(field)

    if not value:
        raise HTTPException(status_code=400, detail=f"{field} is required")

    try:
        return UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field} must be UUID")


# ---------------------------------------------------
# Startup Loader
# ---------------------------------------------------

def load_modules_on_startup(app: FastAPI) -> int:

    db = SessionLocal()

    try:
        loader = ModuleLoaderService(app, db)
        return loader.load_active_modules()

    finally:
        db.close()
