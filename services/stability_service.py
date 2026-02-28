from sqlalchemy.orm import Session

from models.member_layer import StabilityAssessment
from models.users import User


def create_baseline_stability(db: Session, user: User, program_key: str) -> StabilityAssessment:
    assessment = StabilityAssessment(
        user_id=user.id,
        property_id=None,
        program_key=program_key,
        equity_estimate=None,
        equity_health_band=None,
        stability_score=70,
        risk_level=None,
        breakdown_json={"baseline": 70},
    )
    db.add(assessment)
    return assessment
