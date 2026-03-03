from __future__ import annotations

from dataclasses import dataclass

from ai.role_manager import AIRole


@dataclass
class ParsedCommand:
    intent: str
    required_role: AIRole
    execution_request: bool
    params: dict


def parse_command(message: str) -> ParsedCommand:
    text = message.lower().strip()
    if any(k in text for k in ["run daily risk", "daily risk", "risk scan"]):
        return ParsedCommand(
            intent="run_daily_risk_evaluation",
            required_role=AIRole.OPERATE,
            execution_request=True,
            params={},
        )
    if "verify phase" in text or "phase verify" in text:
        return ParsedCommand(
            intent="run_phase_verification",
            required_role=AIRole.INFRA,
            execution_request=True,
            params={"phase_key": "phase7_ai_orchestration"},
        )
    if any(k in text for k in ["migration", "schema change", "alter table"]):
        return ParsedCommand(
            intent="structure_plan",
            required_role=AIRole.STRUCTURE,
            execution_request=False,
            params={"note": "Structural changes must ship as migration files only."},
        )
    return ParsedCommand(
        intent="advisory",
        required_role=AIRole.READ,
        execution_request=False,
        params={},
    )
