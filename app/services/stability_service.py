from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.member_layer import InstallmentStatus, Membership, MembershipInstallment, MembershipStatus, StabilityAssessment


def recalculate_stability(db: Session, user_id: UUID, program_key: str) -> StabilityAssessment:
    membership = (
        db.query(Membership)
        .filter(
            Membership.user_id == user_id,
            Membership.program_key == program_key,
            Membership.status == MembershipStatus.active,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Active membership not found")

    installments = (
        db.query(MembershipInstallment)
        .filter(MembershipInstallment.membership_id == membership.id)
        .all()
    )

    latest = (
        db.query(StabilityAssessment)
        .filter(
            StabilityAssessment.user_id == user_id,
            StabilityAssessment.program_key == program_key,
        )
        .order_by(StabilityAssessment.created_at.desc())
        .first()
    )

    previous_score = latest.stability_score if latest else 70
    paid_cash_count = sum(1 for installment in installments if installment.status == InstallmentStatus.paid_cash)
    missed_count = sum(1 for installment in installments if installment.status == InstallmentStatus.missed)

    new_score = previous_score + 5
    if missed_count > 0:
        new_score -= 10

    new_score = max(0, min(100, new_score))

    assessment = StabilityAssessment(
        user_id=user_id,
        property_id=None,
        program_key=program_key,
        equity_estimate=None,
        equity_health_band=None,
        stability_score=new_score,
        risk_level=None,
        breakdown_json={
            "source": "installment_payment_event",
            "previous_score": previous_score,
            "paid_cash_count": paid_cash_count,
            "missed_count": missed_count,
            "new_score": new_score,
        },
    )
    db.add(assessment)

    membership.good_standing = new_score >= 65
    return assessment
