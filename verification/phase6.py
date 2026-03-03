from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.member_layer import InstallmentStatus, Membership, MembershipInstallment, MembershipStatus
from app.models.users import User
from app.services.escalation_service import evaluate_member_risk


class Phase6Verifier:
    phase_key = "phase6_risk_escalation"

    def verify(self, db: Session, environment: str) -> dict:
        user = User(id=uuid4(), email=f"verification+phase6-{uuid4().hex[:6]}@system.local", hashed_password="x")
        db.add(user)
        db.flush()

        membership = Membership(
            id=uuid4(),
            user_id=user.id,
            program_key="homeowner_protection",
            term_start=date.today(),
            term_end=date.today() + timedelta(days=365),
            annual_price_cents=12000,
            installment_cents=1000,
            status=MembershipStatus.active,
            good_standing=True,
        )
        db.add(membership)
        db.flush()

        db.add(
            MembershipInstallment(
                id=uuid4(),
                membership_id=membership.id,
                due_date=date.today() - timedelta(days=1),
                amount_cents=1000,
                status=InstallmentStatus.missed,
            )
        )
        db.flush()

        first = evaluate_member_risk(db, membership.id)
        second = evaluate_member_risk(db, membership.id)

        db.refresh(membership)
        audit_count = (
            db.query(AuditLog)
            .filter(
                AuditLog.action_type == "escalated_due_to_risk",
                AuditLog.reason_code == f"membership:{membership.id}:escalated_due_to_risk",
            )
            .count()
        )

        checks = {
            "missed_installment_detected": first.get("missed_installments", 0) > 0,
            "good_standing_flipped": membership.good_standing is False,
            "audit_inserted": audit_count == 1,
            "idempotent_second_run": second.get("audit_created") is False and audit_count == 1,
        }

        return {
            "phase_key": self.phase_key,
            "environment": environment,
            "success": all(checks.values()),
            "checks": checks,
            "results": {
                "first": first,
                "second": second,
                "audit_count": audit_count,
            },
        }
