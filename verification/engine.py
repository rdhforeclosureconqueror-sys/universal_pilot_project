import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.system_verification import PhaseVerificationRun, SystemPhase
from verification.phase1 import Phase1Verifier
from verification.phase4 import Phase4Verifier
from verification.phase5 import Phase5Verifier
from verification.phase7_ai_orchestration import Phase7Verifier
from verification.phase6 import Phase6Verifier


class PhaseVerifier(ABC):
    @abstractmethod
    def verify(self, db: Session, environment: str) -> dict:
        raise NotImplementedError


# =====================================================
# Phase Registry
# =====================================================

PHASE_REGISTRY: Dict[str, PhaseVerifier] = {
    "phase1_intake_activation": Phase1Verifier(),
    "phase4_admin_dashboard": Phase4Verifier(),
    "phase5_member_stability_engine": Phase5Verifier(),
    "phase6_risk_escalation": Phase6Verifier(),
    "phase7_ai_orchestration": Phase7Verifier(),
}


class VerificationEngine:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------
    # Environment Resolver
    # -------------------------------------------------

    @staticmethod
    def resolve_environment() -> str:
        return (os.getenv("ENVIRONMENT") or "development").strip()

    # -------------------------------------------------
    # Run Phase Verification
    # -------------------------------------------------

    def run_phase(self, phase_key: str) -> dict:
        verifier = PHASE_REGISTRY.get(phase_key)

        if not verifier:
            raise ValueError(f"Unknown phase: {phase_key}")

        environment = self.resolve_environment()

        # Execute verification logic
        result = verifier.verify(self.db, environment)
        success = bool(result.get("success"))

        # Record verification run
        run = PhaseVerificationRun(
            environment=environment,
            phase_key=phase_key,
            result=result,
            success=success,
        )
        self.db.add(run)

        # Fetch or create phase row
        phase_row = (
            self.db.query(SystemPhase)
            .filter(
                SystemPhase.environment == environment,
                SystemPhase.phase_key == phase_key,
            )
            .first()
        )

        if not phase_row:
            phase_row = SystemPhase(
                environment=environment,
                phase_key=phase_key,
                status="pending",
            )
            self.db.add(phase_row)

        # Update status
        if success:
            phase_row.status = "verified"
            phase_row.verified_at = datetime.now(timezone.utc)
        else:
            phase_row.status = "failed"

        # Commit transaction
        self.db.commit()
        self.db.refresh(run)

        result["run_id"] = str(run.id)
        return result

    # -------------------------------------------------
    # List Phase Statuses
    # -------------------------------------------------

    def list_phase_statuses(self) -> List[dict]:
        environment = self.resolve_environment()

        rows = (
            self.db.query(SystemPhase)
            .filter(SystemPhase.environment == environment)
            .all()
        )

        row_by_key = {row.phase_key: row for row in rows}

        output = []

        for phase_key in PHASE_REGISTRY.keys():
            row = row_by_key.get(phase_key)

            output.append(
                {
                    "phase_key": phase_key,
                    "environment": environment,
                    "status": row.status if row else "pending",
                    "verified_at": (
                        row.verified_at.isoformat()
                        if row and row.verified_at
                        else None
                    ),
                }
            )

        return output
