from __future__ import annotations

from ai.council_prompt import COUNCIL_PROMPT
from ai.command_parser import ParsedCommand


def build_advisory(message: str, parsed: ParsedCommand, context: dict) -> str:
    return (
        f"[{parsed.intent}] Advisory under council doctrine. "
        f"Environment={context.get('environment')} | "
        f"Phases={','.join(context.get('registered_phases', []))}. "
        f"Message='{message[:240]}'. "
        f"Controls: service-layer mediation, immutable audit, idempotent execution, phase verification."
    )


def personality_loaded() -> bool:
    return "Garveyite Council" in COUNCIL_PROMPT
