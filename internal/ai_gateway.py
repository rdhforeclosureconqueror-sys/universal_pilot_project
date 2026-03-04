from __future__ import annotations

from app.services.escalation_service import run_daily_risk_evaluation


def execute_gateway_action(db, intent: str, params: dict | None = None) -> dict:
    params = params or {}
    if intent == "run_daily_risk_evaluation":
        return {"intent": intent, "result": run_daily_risk_evaluation(db)}
    if intent == "run_phase_verification":
        from verification.engine import VerificationEngine

        phase_key = params.get("phase_key", "phase7_ai_orchestration")
        return {"intent": intent, "result": VerificationEngine(db).run_phase(phase_key)}
    if intent in {"advisory", "structure_plan", "noop_status"}:
        return {"intent": intent, "result": {"status": "no_mutation"}}
    raise ValueError(f"Unsupported AI gateway intent: {intent}")
