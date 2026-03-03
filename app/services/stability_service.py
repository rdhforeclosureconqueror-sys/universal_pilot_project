from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.documents import Document
from app.models.member_layer import (
    ContributionCredit,
    InstallmentStatus,
    Membership,
    MembershipInstallment,
    MembershipStatus,
    StabilityAssessment,
)
from app.models.users import User


def create_baseline_stability(db: Session, user: User, program_key: str) -> StabilityAssessment:
    assessment = StabilityAssessment(
        user_id=user.id,
        property_id=None,
        program_key=program_key,
        equity_estimate=None,
        equity_health_band=None,
        stability_score=70,
        risk_level=None,
        breakdown_json={
            "baseline": 70,
            "paid_on_time_count": 0,
            "paid_late_count": 0,
            "missed_count": 0,
            "contribution_credit_count": 0,
            "document_upload_count": 0,
        },
    )
    db.add(assessment)
    return assessment


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

    baseline = 70
    paid_on_time_count = sum(
        1
        for installment in installments
        if installment.status == InstallmentStatus.paid_cash
        and installment.paid_at is not None
        and installment.paid_at.date() <= installment.due_date
    )
    paid_late_count = sum(
        1
        for installment in installments
        if installment.status == InstallmentStatus.paid_cash
        and installment.paid_at is not None
        and installment.paid_at.date() > installment.due_date
    )
    missed_count = sum(1 for installment in installments if installment.status == InstallmentStatus.missed)

    contribution_credit_count = (
        db.query(ContributionCredit)
        .filter(ContributionCredit.membership_id == membership.id)
        .count()
    )
    document_upload_count = db.query(Document).filter(Document.uploaded_by == user_id).count()
    new_score = (
        baseline
        + (paid_on_time_count * 5)
        + (paid_late_count * 2)
        - (missed_count * 10)
        + (contribution_credit_count * 3)
        + (document_upload_count * 2)
    )
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
            "source": "phase5_recalculation",
            "previous_score": latest.stability_score if latest else baseline,
            "baseline": baseline,
            "paid_on_time_count": paid_on_time_count,
            "paid_late_count": paid_late_count,
            "missed_count": missed_count,
            "contribution_credit_count": contribution_credit_count,
            "document_upload_count": document_upload_count,
            "new_score": new_score,
        },
    )
    db.add(assessment)

    membership.good_standing = new_score >= 65
    return assessment
