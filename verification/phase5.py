from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.member_layer import InstallmentStatus, Membership, MembershipInstallment, MembershipStatus, StabilityAssessment
from app.models.users import User
from app.services.stability_service import recalculate_stability


class Phase5Verifier:
    phase_key = "phase5_member_stability_engine"

    def verify(self, db: Session, environment: str) -> dict:
        user = User(id=uuid4(), email=f"verification+phase5-{uuid4().hex[:6]}@system.local", hashed_password="x")
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
                due_date=date.today(),
                amount_cents=1000,
                status=InstallmentStatus.paid_cash,
            )
        )
        db.flush()

        before = db.query(StabilityAssessment).filter(StabilityAssessment.user_id == user.id).count()
        row = recalculate_stability(db, user.id, membership.program_key)
        after = db.query(StabilityAssessment).filter(StabilityAssessment.user_id == user.id).count()

        checks = {
            "assessment_inserted": after == before + 1,
            "score_bounded": 0 <= row.stability_score <= 100,
            "breakdown_present": bool(row.breakdown_json),
        }

        return {
            "phase_key": self.phase_key,
            "environment": environment,
            "success": all(checks.values()),
            "checks": checks,
            "counts": {
                "before": before,
                "after": after,
            },
        }
