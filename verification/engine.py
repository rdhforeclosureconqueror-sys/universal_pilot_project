import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.system_verification import PhaseVerificationRun, SystemPhase
from verification.phase1 import Phase1Verifier


class PhaseVerifier(ABC):
    @abstractmethod
    def verify(self, db: Session, environment: str) -> dict:
        raise NotImplementedError


PHASE_REGISTRY: dict[str, PhaseVerifier] = {
    "phase1_intake_activation": Phase1Verifier(),
}


class VerificationEngine:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def resolve_environment() -> str:
        return os.getenv("ENVIRONMENT", "development").strip() or "development"

    def run_phase(self, phase_key: str) -> dict:
        verifier = PHASE_REGISTRY.get(phase_key)
        if not verifier:
            raise ValueError(f"unknown phase: {phase_key}")

        environment = self.resolve_environment()
        result = verifier.verify(self.db, environment)
        success = bool(result.get("success"))

        run = PhaseVerificationRun(
            environment=environment,
            phase_key=phase_key,
            result=result,
            success=success,
        )
        self.db.add(run)

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

        if success:
            phase_row.status = "verified"
            phase_row.verified_at = datetime.now(timezone.utc)
        else:
            phase_row.status = "failed"

        self.db.commit()
        self.db.refresh(run)

        result["run_id"] = str(run.id)
        return result

    def list_phase_statuses(self) -> list[dict]:
        environment = self.resolve_environment()
        rows = (
            self.db.query(SystemPhase)
            .filter(SystemPhase.environment == environment)
            .all()
        )
        row_by_key = {row.phase_key: row for row in rows}

        output = []
        for phase_key in PHASE_REGISTRY:
            row = row_by_key.get(phase_key)
            output.append(
                {
                    "phase_key": phase_key,
                    "environment": environment,
                    "status": row.status if row else "pending",
                    "verified_at": row.verified_at.isoformat() if row and row.verified_at else None,
                }
            )
        return output
