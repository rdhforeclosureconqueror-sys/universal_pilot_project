from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.stability_service import recalculate_stability
from models.member_layer import InstallmentStatus, Membership, MembershipInstallment


def mark_installment_paid(db: Session, installment_id: UUID) -> MembershipInstallment:
    installment = (
        db.query(MembershipInstallment)
        .filter(MembershipInstallment.id == installment_id)
        .first()
    )
    if not installment:
        raise HTTPException(status_code=404, detail="Installment not found")

    if installment.status == InstallmentStatus.paid_cash:
        return installment

    membership = (
        db.query(Membership)
        .filter(Membership.id == installment.membership_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    installment.status = InstallmentStatus.paid_cash
    installment.paid_at = datetime.now(timezone.utc)

    recalculate_stability(
        db=db,
        user_id=membership.user_id,
        program_key=membership.program_key,
    )

    db.commit()
    db.refresh(installment)
    return installment
