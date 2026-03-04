from __future__ import annotations

import os


def build_context(db) -> dict:
    _ = db
    return {
        "environment": os.getenv("ENVIRONMENT", "development").strip() or "development",
        "registered_phases": [
            "phase1_intake_activation",
            "phase4_admin_dashboard",
            "phase5_member_stability_engine",
            "phase6_risk_escalation",
            "phase7_ai_orchestration",
        ],
        "system": "service_oriented_monolith",
    }
