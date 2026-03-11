# app/services/module_loader_service.py
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
from app.services.module_registry_service import ModuleRegistryService
from app.services.membership_service import create_membership
from app.services.partner_routing_service import route_case_to_partner
from app.services.property_analysis_service import (
    calculate_acquisition_score,
    calculate_equity,
    calculate_ltv,
    calculate_rescue_score,
    classify_intervention,
)
from app.services.property_portfolio_service import (
    add_property_to_portfolio,
    calculate_portfolio_equity,
)
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

from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from db.session import SessionLocal, get_db


class ModuleActionRequest(BaseModel):
    case_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


def _payload_uuid(payload: dict[str, Any], key: str) -> UUID:
    value = payload.get(key)
    if not value:
        raise HTTPException(status_code=400, detail=f"{key} is required")
    try:
        return UUID(str(value))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"{key} must be a UUID") from exc


class DomainServiceBroker:
    """Bounded dispatcher for module actions using existing domain services only."""

    def __init__(self) -> None:
        self._handlers: dict[str, tuple[str, Callable[..., dict[str, Any]], bool]] = {
            "run_daily_risk_evaluation": ("escalation_service", self._run_daily_risk_evaluation, False),
            "upsert_veteran_profile": ("veteran_intelligence_service", self._upsert_veteran_profile, True),
            "scan_veteran_benefits": ("veteran_intelligence_service", self._scan_veteran_benefits, True),
            "generate_veteran_action_plan": ("veteran_intelligence_service", self._generate_veteran_action_plan, True),
            "generate_veteran_documents": ("document_service", self._generate_veteran_documents, True),
            "update_benefit_progress": ("veteran_intelligence_service", self._update_benefit_progress, True),
            "veteran_ai_advisory": ("veteran_intelligence_service", self._veteran_ai_advisory, True),
            "veteran_partner_aggregate_report": ("veteran_intelligence_service", self._veteran_partner_aggregate_report, False),
            "calculate_veteran_benefit_value": ("veteran_intelligence_service", self._calculate_veteran_benefit_value, True),
            "calculate_case_priority": ("foreclosure_intelligence_service", self._calculate_case_priority, True),
            "analyze_property": ("property_analysis_service", self._analyze_property, True),
            "route_case_partner": ("partner_routing_service", self._route_case_partner, True),
            "add_property_to_portfolio": ("property_portfolio_service", self._add_property_to_portfolio, True),
            "portfolio_summary": ("property_portfolio_service", self._portfolio_summary, True),
            "create_membership_profile": ("membership_service", self._create_membership_profile, True),
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

    def validate_required_services(self, required_services: list[str]) -> tuple[bool, str]:
        unknown = sorted(set(required_services) - self.allowed_services)
        if unknown:
            return False, f"unknown required services: {', '.join(unknown)}"
        return True, "required services are valid"

    def execute_action(
        self,
        db: Session,
        *,
        module: ModuleRegistry,
        action_name: str,
        payload: dict[str, Any],
        actor_id: UUID | None = None,
    ) -> dict[str, Any]:

        if action_name not in (module.allowed_actions or []):
            raise HTTPException(status_code=403, detail=f"Action '{action_name}' not allowed for module")

        mapped = self._handlers.get(action_name)

        if not mapped:
            raise HTTPException(status_code=501, detail=f"No safe domain-service mapping for action '{action_name}'")

        service_name, handler, requires_actor = mapped

        if service_name not in (module.required_services or []):
            raise HTTPException(
                status_code=400,
                detail=f"Action '{action_name}' requires service '{service_name}' declared in required_services",
            )

        return handler(db, payload, requires_actor and actor_id is not None, actor_id)

    @staticmethod
    def _run_daily_risk_evaluation(db: Session, payload: dict[str, Any], _requires_actor: bool, _actor_id: UUID | None):
        del payload
        return run_daily_risk_evaluation(db)

    @staticmethod
    def _upsert_veteran_profile(db: Session, payload: dict[str, Any], _requires_actor: bool, actor_id: UUID | None):
        profile = upsert_veteran_profile(db, actor_id=actor_id, payload=payload)
        return {"case_id": str(profile.case_id), "disability_rating": profile.disability_rating}

    @staticmethod
    def _scan_veteran_benefits(db: Session, payload: dict[str, Any], _requires_actor: bool, _actor_id: UUID | None):
        case_id = _payload_uuid(payload, "case_id")
        return match_benefits(db, case_id=case_id)

    @staticmethod
    def _generate_veteran_action_plan(db: Session, payload: dict[str, Any], _requires_actor: bool, _actor_id: UUID | None):
        case_id = _payload_uuid(payload, "case_id")
        return generate_action_plan(db, case_id=case_id)

    @staticmethod
    def _generate_veteran_documents(db: Session, payload: dict[str, Any], requires_actor: bool, actor_id: UUID | None):
        if requires_actor and actor_id is None:
            raise HTTPException(status_code=400, detail="actor_id required")
        case_id = _payload_uuid(payload, "case_id")
        return generate_documents(db, case_id=case_id, actor_id=actor_id)

    @staticmethod
    def _update_benefit_progress(db: Session, payload: dict[str, Any], _requires_actor: bool, actor_id: UUID | None):
        case_id = _payload_uuid(payload, "case_id")
        return update_benefit_progress(
            db,
            case_id=case_id,
            benefit_name=payload.get("benefit_name", ""),
            status=payload.get("status", "NOT_STARTED"),
            status_notes=payload.get("status_notes"),
            actor_id=actor_id,
        )

    @staticmethod
    def _veteran_ai_advisory(db: Session, payload: dict[str, Any], _requires_actor: bool, _actor_id: UUID | None):
        case_id = _payload_uuid(payload, "case_id")
        return get_advisory(db, case_id=case_id, question=payload.get("question", ""))


class ModuleLoaderService:

    def __init__(self, app: FastAPI, db: Session):
        self.app = app
        self.db = db
        self.registry_service = ModuleRegistryService(db)
        self.domain_broker = DomainServiceBroker()

    def load_active_modules(self) -> int:

        active_modules = (
            self.db.query(ModuleRegistry)
            .filter(
                ModuleRegistry.is_active.is_(True),
                ModuleRegistry.status == "active",
            )
            .all()
        )

        if not hasattr(self.app.state, "dynamic_module_routes"):
            self.app.state.dynamic_module_routes = set()

        loaded_count = 0

        for module in active_modules:

            route_key = f"{module.module_name}:{module.version}"

            if route_key in self.app.state.dynamic_module_routes:
                continue

            self._register_module_router(module)

            self.app.state.dynamic_module_routes.add(route_key)

            loaded_count += 1

        self.db.commit()

        return loaded_count

    def _register_module_router(self, module: ModuleRegistry) -> None:

        router = APIRouter(
            prefix=f"/modules/{module.module_name}",
            tags=["dynamic-modules"],
        )

        @router.post("/actions/{action_name}")
        def invoke_module_action(
            action_name: str,
            request: ModuleActionRequest,
            db: Session = Depends(get_db),
            user: User = Depends(get_current_user),
        ):

            policy_authorizer = PolicyAuthorizer(db)

            if not request.case_id:
                raise HTTPException(status_code=400, detail="case_id required")

            policy_authorizer.require_case_action(
                user=user,
                case_id=request.case_id,
                action=f"modules.{module.module_name}.{action_name}",
            )

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
                    action_type="module_action_invoked",
                    reason_code=f"module_action:{module.module_name}:{action_name}",
                    before_state={},
                    after_state={"result": result},
                    policy_version_id=None,
                )
            )

            db.commit()

            return result

        self.app.include_router(router)


def load_modules_on_startup(app: FastAPI) -> int:

    db = SessionLocal()

    try:
        return ModuleLoaderService(app, db).load_active_modules()
    finally:
        db.close()