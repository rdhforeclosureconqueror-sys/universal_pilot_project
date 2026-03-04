from __future__ import annotations

from datetime import datetime
from typing import Callable
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.module_registry import ModuleRegistry
from app.schemas.module_registry import ModuleSpec

PolicyValidationHook = Callable[[Session, ModuleRegistry], tuple[bool, str]]


class ModuleRegistryService:
    def __init__(self, db: Session):
        self.db = db

    def create_module(self, spec: ModuleSpec, actor_id: UUID | None = None) -> ModuleRegistry:
        existing = (
            self.db.query(ModuleRegistry)
            .filter(
                ModuleRegistry.module_name == spec.module_name,
                ModuleRegistry.version == spec.version,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Module version already exists")

        module = ModuleRegistry(
            module_name=spec.module_name,
            module_type=spec.module_type,
            version=spec.version,
            permissions=spec.permissions,
            required_services=spec.required_services,
            data_schema=spec.data_schema,
            allowed_actions=spec.allowed_actions,
            status="draft",
            policy_validation_status="pending",
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.db.add(module)
        self.db.flush()

        self._log_lifecycle_event(
            actor_id=actor_id,
            event_type="module_registry.created",
            reason_code="module_created",
            before_state={},
            after_state={
                "module_id": str(module.id),
                "module_name": module.module_name,
                "version": module.version,
                "status": module.status,
            },
        )
        self.db.commit()
        self.db.refresh(module)
        return module

    def validate_module(self, module_id: UUID, actor_id: UUID | None = None) -> ModuleRegistry:
        module = self._get_or_404(module_id)
        validation_errors = self._validation_errors(module)

        previous_status = module.status
        module.validation_errors = validation_errors
        module.updated_by = actor_id
        module.updated_at = datetime.utcnow()
        module.status = "validated" if not validation_errors else "draft"

        self._log_lifecycle_event(
            actor_id=actor_id,
            event_type="module_registry.validated",
            reason_code="module_validated" if not validation_errors else "module_validation_failed",
            before_state={"status": previous_status},
            after_state={
                "module_id": str(module.id),
                "module_name": module.module_name,
                "version": module.version,
                "status": module.status,
                "validation_errors": validation_errors,
            },
        )

        self.db.commit()
        self.db.refresh(module)
        return module

    def activate_module(
        self,
        module_id: UUID,
        *,
        actor_id: UUID | None = None,
        policy_validation_hook: PolicyValidationHook | None = None,
    ) -> ModuleRegistry:
        module = self._get_or_404(module_id)

        if module.status != "validated":
            module = self.validate_module(module_id=module.id, actor_id=actor_id)

        if module.validation_errors:
            raise HTTPException(status_code=400, detail="Module failed validation")

        policy_hook = policy_validation_hook or self._default_policy_validation_hook
        allowed, reason = policy_hook(self.db, module)
        module.policy_validation_status = "approved" if allowed else "denied"
        module.updated_by = actor_id

        self._log_lifecycle_event(
            actor_id=actor_id,
            event_type="module_registry.policy_validation",
            reason_code="policy_approved" if allowed else "policy_denied",
            before_state={},
            after_state={
                "module_id": str(module.id),
                "module_name": module.module_name,
                "version": module.version,
                "allowed": allowed,
                "reason": reason,
            },
        )

        if not allowed:
            self.db.commit()
            raise HTTPException(status_code=403, detail=f"Policy validation denied: {reason}")

        (
            self.db.query(ModuleRegistry)
            .filter(
                ModuleRegistry.module_name == module.module_name,
                ModuleRegistry.id != module.id,
                ModuleRegistry.is_active.is_(True),
            )
            .update({"is_active": False, "status": "deprecated"}, synchronize_session=False)
        )

        module.status = "active"
        module.is_active = True
        module.activated_at = datetime.utcnow()

        self._log_lifecycle_event(
            actor_id=actor_id,
            event_type="module_registry.activated",
            reason_code="module_activated",
            before_state={},
            after_state={
                "module_id": str(module.id),
                "module_name": module.module_name,
                "version": module.version,
                "status": module.status,
                "activated_at": module.activated_at.isoformat() if module.activated_at else None,
            },
        )

        self.db.commit()
        self.db.refresh(module)
        return module

    def _get_or_404(self, module_id: UUID) -> ModuleRegistry:
        module = self.db.query(ModuleRegistry).filter(ModuleRegistry.id == module_id).first()
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
        return module

    @staticmethod
    def _validation_errors(module: ModuleRegistry) -> list[str]:
        errors: list[str] = []
        if not module.module_name:
            errors.append("module_name is required")
        if not module.module_type:
            errors.append("module_type is required")
        if not isinstance(module.permissions, list) or not module.permissions:
            errors.append("permissions must be a non-empty list")
        if not isinstance(module.required_services, list) or not module.required_services:
            errors.append("required_services must be a non-empty list")
        if not isinstance(module.data_schema, dict) or not module.data_schema:
            errors.append("data_schema must be a non-empty object")
        if not isinstance(module.allowed_actions, list) or not module.allowed_actions:
            errors.append("allowed_actions must be a non-empty list")
        return errors

    @staticmethod
    def _default_policy_validation_hook(db: Session, module: ModuleRegistry) -> tuple[bool, str]:
        del db
        wildcard_permission = any(p == "*" for p in module.permissions or [])
        wildcard_action = any(a == "*" for a in module.allowed_actions or [])
        if wildcard_permission or wildcard_action:
            return False, "wildcard permissions/actions are not allowed"
        return True, "policy checks passed"

    def _log_lifecycle_event(
        self,
        *,
        actor_id: UUID | None,
        event_type: str,
        reason_code: str,
        before_state: dict,
        after_state: dict,
    ) -> None:
        audit_log = AuditLog(
            id=uuid4(),
            case_id=None,
            actor_id=actor_id,
            actor_is_ai=False,
            action_type=event_type,
            reason_code=reason_code,
            before_state=before_state,
            after_state=after_state,
            policy_version_id=None,
        )
        self.db.add(audit_log)
