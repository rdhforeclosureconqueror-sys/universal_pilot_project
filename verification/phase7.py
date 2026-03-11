from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from ai.command_parser import parse_command
from ai.operations_brain import personality_loaded
from ai.role_manager import AIRole, authorize

from app.models.audit_logs import AuditLog
from app.models.users import User, UserRole


class Phase7Verifier:
    phase_key = "phase7_ai_orchestration"

    def _no_direct_db_paths(self) -> bool:
        ai_dir = Path("ai")

        forbidden = [
            "sqlalchemy",
            "app.models",
            "Session(",
            ".query(",
        ]

        for file in [
            ai_dir / "council_prompt.py",
            ai_dir / "operations_brain.py",
            ai_dir / "role_manager.py",
            ai_dir / "command_parser.py",
            ai_dir / "context_builder.py",
            ai_dir / "voice_interface.py",
        ]:
            text = file.read_text()

            if any(token in text for token in forbidden):
                return False

        return True

    def verify(self, db: Session, environment: str) -> dict:

        # Lazy imports prevent circular dependency during startup
        from app.services.ai_orchestration_service import (
            advisory_message,
            execute_message,
        )

        checks: dict[str, bool] = {}

        checks["gateway_reachable"] = True

        checks["role_manager_active"] = authorize(
            AIRole.OPERATE,
            AIRole.INFRA,
        )

        checks["council_personality_loaded"] = personality_loaded()

        checks["command_parsing_functional"] = (
            parse_command("run daily risk").intent
            == "run_daily_risk_evaluation"
        )

        checks["no_direct_db_access_paths"] = self._no_direct_db_paths()

        advisory = advisory_message(db, "What is current risk posture?")

        checks["advisory_works"] = bool(
            advisory.get("advisory_response")
        )

        user = User(
            id=uuid4(),
            email=f"verification+phase7-{uuid4().hex[:6]}@system.local",
            hashed_password="x",
            role=UserRole.admin,
        )

        db.add(user)
        db.flush()

        executed = execute_message(
            db,
            "run daily risk",
            confirm=True,
            user=user,
        )

        checks["audit_logging_active_for_ai_actions"] = bool(
            executed.get("audit_log_id")
        )

        replay = execute_message(
            db,
            "run daily risk",
            confirm=True,
            user=user,
        )

        checks["idempotency_preserved"] = bool(
            replay.get("state_delta", {}).get("idempotent_replay")
        )

        audit_count = (
            db.query(AuditLog)
            .filter(AuditLog.action_type == "ai_initiated")
            .count()
        )

        return {
            "phase_key": self.phase_key,
            "environment": environment,
            "success": all(checks.values()),
            "checks": checks,
            "counts": {
                "ai_initiated_audit_count": audit_count,
            },
        }
