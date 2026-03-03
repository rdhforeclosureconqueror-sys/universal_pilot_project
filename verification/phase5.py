from sqlalchemy.orm import Session

from app.services.stability_service import recalculate_stability
from app.models.member_layer import (
    Membership,
    MembershipInstallment,
    ContributionCredit,
    StabilityAssessment,
)


class Phase5Verifier:
    phase_key = "phase5_member_stability_engine"

    def verify(self, db: Session, environment: str) -> dict:
        checks: dict[str, bool] = {}

        # 1️⃣ Confirm membership model loads
        membership_exists = db.query(Membership).limit(1).all()
        checks["membership_query_ok"] = membership_exists is not None

        # 2️⃣ Confirm installment model loads
        installments = db.query(MembershipInstallment).limit(1).all()
        checks["installment_query_ok"] = installments is not None

        # 3️⃣ Confirm contribution credits query works
        credits = db.query(ContributionCredit).limit(1).all()
        checks["contribution_credit_query_ok"] = credits is not None

        # 4️⃣ Confirm stability assessment table accessible
        assessments = db.query(StabilityAssessment).limit(1).all()
        checks["stability_assessment_query_ok"] = assessments is not None

        # 5️⃣ Confirm recalculation function callable (smoke test only)
        checks["stability_function_available"] = callable(recalculate_stability)

        return {
            "phase_key": self.phase_key,
            "environment": environment,
            "success": all(checks.values()),
            "checks": checks,
            "counts": {
                "memberships_checked": len(membership_exists),
                "installments_checked": len(installments),
                "credits_checked": len(credits),
                "assessments_checked": len(assessments),
            },
        }
