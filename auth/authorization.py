from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from audit.logger import log_audit
from app.models.cases import Case
from app.models.policy_versions import PolicyVersion
from app.models.role_sessions import RoleSession
from app.models.users import User


class PolicyAuthorizer:
    def __init__(self, db: Session):
        self.db = db

    def assume_role(
        self,
        *,
        user: User,
        role_name: str,
        case_id: str | None = None,
        program_key: str | None = None,
        duration_minutes: int = 30,
    ) -> RoleSession:
        if duration_minutes <= 0 or duration_minutes > 240:
            raise HTTPException(status_code=400, detail="duration_minutes must be between 1 and 240")

        policy_config = self._resolve_policy_config(case_id=case_id, program_key=program_key)
        eligible_roles = self._eligible_roles_for_identity(policy_config=policy_config, identity_role=user.role.value if user.role else "")
        if role_name not in eligible_roles:
            raise HTTPException(status_code=403, detail="Role assumption denied by policy eligibility")

        role_session = RoleSession(
            user_id=user.id,
            role_name=role_name,
            scope_case_id=UUID(case_id) if case_id else None,
            scope_program_key=program_key,
            expires_at=datetime.utcnow() + timedelta(minutes=duration_minutes),
        )
        self.db.add(role_session)
        self.db.commit()
        self.db.refresh(role_session)
        return role_session

    def require_case_action(self, *, user: User, case_id: str, action: str) -> RoleSession:
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        policy = self.db.query(PolicyVersion).filter(PolicyVersion.id == case.policy_version_id).first()
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found for case")

        active_session = (
            self.db.query(RoleSession)
            .filter(RoleSession.user_id == user.id)
            .filter(RoleSession.revoked_at.is_(None))
            .filter(RoleSession.expires_at > datetime.utcnow())
            .filter((RoleSession.scope_case_id.is_(None)) | (RoleSession.scope_case_id == case.id))
            .filter((RoleSession.scope_program_key.is_(None)) | (RoleSession.scope_program_key == case.program_key) | (RoleSession.scope_program_key == case.program_type))
            .order_by(RoleSession.expires_at.desc())
            .first()
        )

        if not active_session:
            self._audit_decision(
                case_id=case_id,
                actor_id=user.id,
                policy_version_id=policy.id,
                action=action,
                reason_code="no_active_role_session",
                allowed=False,
            )
            self.db.commit()
            raise HTTPException(status_code=403, detail="AssumeRole required")

        allowed_roles = (policy.config_json or {}).get("permissions", {}).get("actions", {}).get(action, [])
        if active_session.role_name not in allowed_roles:
            self._audit_decision(
                case_id=case_id,
                actor_id=user.id,
                policy_version_id=policy.id,
                action=action,
                reason_code="action_not_allowed_by_policy",
                allowed=False,
            )
            self.db.commit()
            raise HTTPException(status_code=403, detail="Denied by policy")

        self._audit_decision(
            case_id=case_id,
            actor_id=user.id,
            policy_version_id=policy.id,
            action=action,
            reason_code="allowed_by_policy",
            allowed=True,
            role_session_id=str(active_session.id),
        )
        self.db.commit()
        return active_session

    def _resolve_policy_config(self, *, case_id: str | None, program_key: str | None) -> dict:
        if case_id:
            case = self.db.query(Case).filter(Case.id == case_id).first()
            if not case:
                raise HTTPException(status_code=404, detail="Case not found")
            policy = self.db.query(PolicyVersion).filter(PolicyVersion.id == case.policy_version_id).first()
            if not policy:
                raise HTTPException(status_code=404, detail="Policy not found for case")
            return policy.config_json or {}

        if program_key:
            policy = (
                self.db.query(PolicyVersion)
                .filter(PolicyVersion.program_key == program_key, PolicyVersion.is_active.is_(True))
                .first()
            )
            if not policy:
                raise HTTPException(status_code=404, detail="Active policy not found for program")
            return policy.config_json or {}

        raise HTTPException(status_code=400, detail="case_id or program_key is required")

    @staticmethod
    def _eligible_roles_for_identity(*, policy_config: dict, identity_role: str) -> list[str]:
        eligibility = (policy_config or {}).get("role_eligibility", {})
        return eligibility.get(identity_role, [identity_role])

    def _audit_decision(
        self,
        *,
        case_id: str,
        actor_id,
        policy_version_id,
        action: str,
        reason_code: str,
        allowed: bool,
        role_session_id: str | None = None,
    ):
        log_audit(
            db=self.db,
            case_id=case_id,
            actor_id=actor_id,
            action_type="authorization_decision",
            reason_code=reason_code,
            before_state={},
            after_state={
                "action": action,
                "allowed": allowed,
                "role_session_id": role_session_id,
            },
            policy_version_id=policy_version_id,
        )
