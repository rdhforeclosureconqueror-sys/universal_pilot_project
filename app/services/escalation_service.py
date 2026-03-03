from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.cases import Case
from app.models.member_layer import InstallmentStatus, Membership, MembershipInstallment, MembershipStatus, StabilityAssessment
from app.services.workflow_service import advance_to_risk_stage

RISK_STABILITY_THRESHOLD = 65


def evaluate_member_risk(db: Session, membership_id: UUID) -> dict:
    membership = db.query(Membership).filter(Membership.id == membership_id).first()
    if not membership:
        return {"error": "membership_not_found", "membership_id": str(membership_id)}

    missed_count = (
        db.query(MembershipInstallment)
        .filter(
            MembershipInstallment.membership_id == membership.id,
            MembershipInstallment.status == InstallmentStatus.missed,
        )
        .count()
    )

    latest_assessment = (
        db.query(StabilityAssessment)
        .filter(
            StabilityAssessment.user_id == membership.user_id,
            StabilityAssessment.program_key == membership.program_key,
        )
        .order_by(desc(StabilityAssessment.created_at))
        .first()
    )
    stability_score = latest_assessment.stability_score if latest_assessment else None

    risk_triggered = (
        missed_count > 0
        or (stability_score is not None and stability_score < RISK_STABILITY_THRESHOLD)
    )

    audit_created = False
    workflow_escalated = False
    if risk_triggered:
        if membership.good_standing:
            membership.good_standing = False

            reason_code = f"membership:{membership.id}:escalated_due_to_risk"
            existing = (
                db.query(AuditLog.id)
                .filter(
                    AuditLog.action_type == "escalated_due_to_risk",
                    AuditLog.reason_code == reason_code,
                )
                .first()
            )
            if not existing:
                db.add(
                    AuditLog(
                        case_id=None,
                        actor_id=None,
                        actor_is_ai=False,
                        action_type="escalated_due_to_risk",
                        reason_code=reason_code,
                        before_state={"entity_type": "membership", "entity_id": str(membership.id), "good_standing": True},
                        after_state={
                            "entity_type": "membership",
                            "entity_id": str(membership.id),
                            "action": "escalated_due_to_risk",
                            "metadata": {
                                "missed_installments": missed_count,
                                "latest_stability_score": stability_score,
                            },
                            "good_standing": False,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        },
                        policy_version_id=None,
                    )
                )
                audit_created = True

        case = (
            db.query(Case)
            .filter(
                Case.created_by == membership.user_id,
                Case.program_key == membership.program_key,
            )
            .order_by(desc(Case.created_at))
            .first()
        )
        if case:
            workflow_escalated = advance_to_risk_stage(db, case.id)

    db.flush()

    return {
        "membership_id": str(membership.id),
        "risk_triggered": risk_triggered,
        "missed_installments": missed_count,
        "stability_score": stability_score,
        "good_standing": bool(membership.good_standing),
        "audit_created": audit_created,
        "workflow_escalated": workflow_escalated,
    }


def run_daily_risk_evaluation(db: Session) -> dict:
    memberships = (
        db.query(Membership)
        .filter(Membership.status == MembershipStatus.active)
        .all()
    )

    processed = 0
    triggered = 0
    audits_created = 0
    escalated = 0

    for membership in memberships:
        result = evaluate_member_risk(db, membership.id)
        if result.get("error"):
            continue
        processed += 1
        if result["risk_triggered"]:
            triggered += 1
        if result["audit_created"]:
            audits_created += 1
        if result["workflow_escalated"]:
            escalated += 1

    return {
        "processed_memberships": processed,
        "risk_triggered": triggered,
        "audit_logs_created": audits_created,
        "workflow_escalations": escalated,
    }
