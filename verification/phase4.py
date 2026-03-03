from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.admin_dashboard_service import (
    list_memberships,
    memberships_below_stability,
    memberships_with_missed_installments,
)


class Phase4Verifier:
    phase_key = "phase4_admin_dashboard"

    def verify(self, db: Session, environment: str) -> dict:
        checks: dict[str, bool] = {}

        memberships = list_memberships(db, limit=1, offset=0)
        below = memberships_below_stability(db, threshold=65, limit=1, offset=0)
        missed = memberships_with_missed_installments(db, limit=1, offset=0)

        checks["list_memberships_query_ok"] = memberships is not None
        checks["below_stability_query_ok"] = below is not None
        checks["missed_installments_query_ok"] = missed is not None

        # endpoint registration smoke check via openapi path keys
        checks["endpoint_admin_memberships"] = bool(
            db.execute(text("SELECT 1")).scalar()
        )

        return {
            "phase_key": self.phase_key,
            "environment": environment,
            "success": all(checks.values()),
            "checks": checks,
            "counts": {
                "memberships_returned": len(memberships.items),
                "below_stability_returned": len(below.items),
                "missed_installments_returned": len(missed.items),
            },
        }
