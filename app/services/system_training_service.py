from __future__ import annotations

from app.models.housing_intelligence import TrainingGuideStep


SYSTEM_STEPS = [
    {
        "step_id": "case_create",
        "step_title": "Create Homeowner Case",
        "description": "Create a new case record to start homeowner intervention lifecycle.",
        "related_endpoint": "/cases/",
        "role_required": "case_worker",
    },
    {
        "step_id": "document_upload",
        "step_title": "Upload Case Documents",
        "description": "Attach hardship, notice, and mortgage evidence to support intervention decisions.",
        "related_endpoint": "/documents/",
        "role_required": "case_worker",
    },
    {
        "step_id": "property_analysis",
        "step_title": "Run Property Analysis",
        "description": "Analyze equity, LTV, and intervention classification for foreclosure strategy.",
        "related_endpoint": "/foreclosure/analyze-property",
        "role_required": "case_worker",
    },
    {
        "step_id": "partner_routing",
        "step_title": "Route to Partners",
        "description": "Route cases to legal, loan-mod, nonprofit, or acquisition partners.",
        "related_endpoint": "/partners/route-case",
        "role_required": "referral_coordinator",
    },
    {
        "step_id": "membership_management",
        "step_title": "Manage Membership",
        "description": "Create and track cooperative membership status and equity shares.",
        "related_endpoint": "/membership/create",
        "role_required": "admin",
    },
    {
        "step_id": "portfolio_tracking",
        "step_title": "Track Portfolio Properties",
        "description": "Add and monitor acquired/stabilized properties in portfolio.",
        "related_endpoint": "/portfolio/summary",
        "role_required": "admin",
    },
    {
        "step_id": "impact_analytics",
        "step_title": "Review Impact Analytics",
        "description": "Review summary and opportunity map metrics for impact reporting.",
        "related_endpoint": "/impact/housing-summary",
        "role_required": "audit_steward",
    },
]


def get_system_overview() -> dict:
    return {
        "system": "Universal Pilot",
        "phase": "phase9_foreclosure_housing_os",
        "overview": "Policy-controlled housing intervention operating system with guided lifecycle from intake to impact analytics.",
        "total_steps": len(SYSTEM_STEPS),
    }


def get_workflow_guide() -> list[dict]:
    return SYSTEM_STEPS


def get_guide_step(step_id: str) -> dict | None:
    for step in SYSTEM_STEPS:
        if step["step_id"] == step_id:
            return step
    return None


def materialize_training_steps() -> list[TrainingGuideStep]:
    return [TrainingGuideStep(**step) for step in SYSTEM_STEPS]
