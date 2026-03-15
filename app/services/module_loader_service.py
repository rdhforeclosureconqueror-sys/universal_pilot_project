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
from app.services.property_analysis_service import calculate_acquisition_score, calculate_equity, calculate_ltv, calculate_rescue_score, classify_intervention
from app.services.partner_routing_service import route_case_to_partner
from app.services.property_portfolio_service import add_property_to_portfolio, calculate_portfolio_equity
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
        raise HTTPException(
            status_code=400,
            detail=f"{key} must be a UUID",
        ) from exc


class DomainServiceBroker:
    """Dispatcher that safely maps module actions to platform services."""

    def __init__(self) -> None:

        self._handlers: dict[str, tuple[str, Callable[..., dict[str, Any]], bool]] = {
            "run_daily_risk_evaluation": (
                "escalation_service",
                self._run_daily_risk_evaluation,
                False,
            ),
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
            "escalation_service",
            "foreclosure_intelligence_service",
            "property_analysis_service",
            "partner_routing_service",
            "property_portfolio_service",
            "membership_service",
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
            raise HTTPException(
                status_code=403,
                detail=f"Action '{action_name}' not allowed for module",
            )

        mapped = self._handlers.get(action_name)

        if not mapped:
            raise HTTPException(
                status_code=501,
                detail=f"No safe mapping for action '{action_name}'",
            )

        service_name, handler, requires_actor = mapped

        if service_name not in (module.required_services or []):
            raise HTTPException(
                status_code=400,
                detail=f"Action '{action_name}' requires service '{service_name}'",
            )

        return handler(
            db,
            payload,
            requires_actor and actor_id is not None,
            actor_id,
        )

    # ---------- DOMAIN HANDLERS ----------

    @staticmethod
    def _run_daily_risk_evaluation(
        db: Session,
        payload: dict[str, Any],
        _requires_actor: bool,
        _actor_id: UUID | None,
    ) -> dict[str, Any]:

        del payload
        return run_daily_risk_evaluation(db)

    @staticmethod
    def _upsert_veteran_profile(db: Session, payload: dict[str, Any], _requires_actor: bool, actor_id: UUID | None) -> dict[str, Any]:
        profile = upsert_veteran_profile(db, actor_id=actor_id, payload=payload)
        return {"case_id": str(profile.case_id), "disability_rating": profile.disability_rating}

    @staticmethod
    def _scan_veteran_benefits(db: Session, payload: dict[str, Any], _requires_actor: bool, _actor_id: UUID | None) -> dict[str, Any]:
        case_id = _payload_uuid(payload, "case_id")
        return match_benefits(db, case_id=case_id)

    @staticmethod
    def _generate_veteran_action_plan(db: Session, payload: dict[str, Any], _requires_actor: bool, _actor_id: UUID | None) -> dict[str, Any]:
        case_id = _payload_uuid(payload, "case_id")
        return generate_action_plan(db, case_id=case_id)

    @staticmethod
    def _generate_veteran_documents(db: Session, payload: dict[str, Any], requires_actor: bool, actor_id: UUID | None) -> dict[str, Any]:
        if requires_actor and actor_id is None:
            raise HTTPException(status_code=400, detail="actor_id required")
        case_id = _payload_uuid(payload, "case_id")
        return generate_documents(db, case_id=case_id, actor_id=actor_id)

    @staticmethod
    def _update_benefit_progress(db: Session, payload: dict[str, Any], _requires_actor: bool, actor_id: UUID | None) -> dict[str, Any]:
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
    def _veteran_ai_advisory(db: Session, payload: dict[str, Any], _requires_actor: bool, _actor_id: UUID | None) -> dict[str, Any]:
        case_id = _payload_uuid(payload, "case_id")
        return get_advisory(db, case_id=case_id, question=payload.get("question", ""))

    @staticmethod
    def _veteran_partner_aggregate_report(db: Session, payload: dict[str, Any], _requires_actor: bool, _actor_id: UUID | None) -> dict[str, Any]:
        return {"rows": partner_aggregate_report(db, state_of_residence=payload.get("state_of_residence"))}

    @staticmethod
    def _calculate_veteran_benefit_value(db: Session, payload: dict[str, Any], _requires_actor: bool, _actor_id: UUID | None) -> dict[str, Any]:
        case_id = _payload_uuid(payload, "case_id")
        return calculate_benefit_value(db, case_id=case_id)

    @staticmethod
    def _calculate_case_priority(db: Session, payload: dict[str, Any], _requires_actor: bool, _actor_id: UUID | None) -> dict[str, Any]:
        case_id = _payload_uuid(payload, "case_id")
        return calculate_case_priority(db, case_id=case_id)

    @staticmethod
    def _analyze_property(db: Session, payload: dict[str, Any], _requires_actor: bool, _actor_id: UUID | None) -> dict[str, Any]:
        equity = calculate_equity(estimated_property_value=float(payload.get("estimated_property_value", 0)), loan_balance=float(payload.get("loan_balance", 0)))
        ltv = calculate_ltv(loan_balance=float(payload.get("loan_balance", 0)), estimated_property_value=float(payload.get("estimated_property_value", 0)))
        rescue_score = calculate_rescue_score(
            arrears_amount=float(payload.get("arrears_amount", 0)),
            homeowner_income=float(payload.get("homeowner_income", 0)),
            foreclosure_stage=str(payload.get("foreclosure_stage", "pre_foreclosure")),
        )
        acquisition_score = calculate_acquisition_score(equity=equity, ltv=ltv, foreclosure_stage=str(payload.get("foreclosure_stage", "pre_foreclosure")))
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
    def _route_case_partner(
        db: Session,
        payload: dict[str, Any],
        _requires_actor: bool,
        actor_id: UUID | None,
    ) -> dict[str, Any]:

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
    def _add_property_to_portfolio(
        db: Session,
        payload: dict[str, Any],
        _requires_actor: bool,
        actor_id: UUID | None,
    ) -> dict[str, Any]:

        asset = add_property_to_portfolio(db, payload=payload, actor_id=actor_id)

        return {
            "property_asset_id": str(asset.id),
        }

    @staticmethod
    def _portfolio_summary(
        db: Session,
        payload: dict[str, Any],
        _requires_actor: bool,
        _actor_id: UUID | None,
    ) -> dict[str, Any]:

        del payload

        return calculate_portfolio_equity(db)

    @staticmethod
    def _create_membership_profile(
        db: Session,
        payload: dict[str, Any],
        _requires_actor: bool,
        actor_id: UUID | None,
    ) -> dict[str, Any]:

        profile = create_membership(
            db,
            user_id=_payload_uuid(payload, "user_id"),
            case_id=_payload_uuid(payload, "case_id"),
            membership_type=str(payload.get("membership_type", "cooperative")),
            actor_id=actor_id,
        )

        return {
            "membership_profile_id": str(profile.id),
        }


class ModuleLoaderService:

    def __init__(self, app: FastAPI, db: Session):
        self.app = app
        self.db = db
        self.registry_service = ModuleRegistryService(db)
        self.domain_broker = DomainServiceBroker()

    def load_active_modules(self) -> int:
        active_modules = (
            self.db.query(ModuleRegistry)
            .filter(ModuleRegistry.is_active.is_(True), ModuleRegistry.status == "active")
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
                module=live_module,
                action_name=action_name,
                payload=request.payload,
                actor_id=user.id,
            )

            try:
                case_uuid = UUID(request.case_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="case_id must be a valid UUID") from exc

            db.add(
                AuditLog(
                    id=uuid4(),
                    case_id=case_uuid,
                    actor_id=user.id,
                    actor_is_ai=False,
                    action_type="module_action_invoked",
                    reason_code=f"module_action:{live_module.module_name}:{action_name}",
                    before_state={
                        "module_name": live_module.module_name,
                        "version": live_module.version,
                        "action": action_name,
                    },
                    after_state={"result": result},
                    policy_version_id=None,
                )
            )
            db.commit()

            return {
                "status": "success",
                "module_name": live_module.module_name,
                "version": live_module.version,
                "action": action_name,
                "result": result,
            }

        self.app.include_router(router)

    def _log_load_event(self, *, module: ModuleRegistry, reason_code: str, after_state: dict[str, Any]) -> None:
        self.db.add(
            AuditLog(
                id=uuid4(),
                case_id=None,
                actor_id=None,
                actor_is_ai=False,
                action_type="module_loader",
                reason_code=reason_code,
                before_state={
                    "module_name": module.module_name,
                    "version": module.version,
                    "status": module.status,
                },
                after_state=after_state,
                policy_version_id=None,
            )
        )


def load_modules_on_startup(app: FastAPI) -> int:
    db = SessionLocal()
    try:
        return ModuleLoaderService(app, db).load_active_modules()
    finally:
        db.close()


def _payload_uuid(payload: dict[str, Any], field: str) -> UUID:
    value = payload.get(field)
    if not value:
        raise HTTPException(status_code=400, detail=f"{field} is required")
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field} must be a valid UUID") from exc
