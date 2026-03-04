from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.member_layer import InstallmentStatus, Membership, MembershipInstallment
from app.services.escalation_service import evaluate_member_risk
from app.services.stability_service import recalculate_stability


class PaymentProcessingError(ValueError):
    """Raised when a payment webhook cannot be mapped to a payable installment."""


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
    evaluate_member_risk(db=db, membership_id=membership.id)

    db.commit()
    db.refresh(installment)
    return installment


def evaluate_member_risk(db: Session, membership_id: UUID) -> None:
    membership = db.query(Membership).filter(Membership.id == membership_id).first()
    if not membership:
        raise PaymentProcessingError(f"Membership not found for id={membership_id}")

    has_missed = (
        db.query(MembershipInstallment.id)
        .filter(
            MembershipInstallment.membership_id == membership.id,
            MembershipInstallment.status == InstallmentStatus.missed,
        )
        .first()
        is not None
    )

    before_standing = bool(membership.good_standing)
    if has_missed:
        membership.good_standing = False

    reason_code = f"membership_risk_{membership.id}_{int(has_missed)}"
    existing_audit = (
        db.query(AuditLog.id)
        .filter(
            AuditLog.reason_code == reason_code,
            AuditLog.action_type == "membership_risk_evaluated",
        )
        .first()
    )
    if existing_audit:
        return

    db.add(
        AuditLog(
            case_id=None,
            actor_id=None,
            actor_is_ai=False,
            action_type="membership_risk_evaluated",
            reason_code=reason_code,
            before_state={"good_standing": before_standing},
            after_state={"good_standing": bool(membership.good_standing), "has_missed_installments": has_missed},
            policy_version_id=None,
        )
    )



def handle_successful_payment(
    db: Session,
    stripe_invoice_id: str,
    stripe_customer_id: str,
    amount_paid_cents: int,
) -> None:
    installment = (
        db.query(MembershipInstallment)
        .filter(MembershipInstallment.stripe_invoice_id == stripe_invoice_id)
        .first()
    )
    if not installment:
        raise PaymentProcessingError(f"Installment not found for stripe_invoice_id={stripe_invoice_id}")

    if installment.status == InstallmentStatus.paid_cash:
        return

    membership = db.query(Membership).filter(Membership.id == installment.membership_id).first()
    if not membership:
        raise PaymentProcessingError(f"Membership not found for installment id={installment.id}")

    previous_status = installment.status
    installment.status = InstallmentStatus.paid_cash
    installment.paid_at = datetime.now(timezone.utc)
    installment.amount_paid_cents = amount_paid_cents

    overdue_remaining = (
        db.query(MembershipInstallment.id)
        .filter(
            MembershipInstallment.membership_id == membership.id,
            MembershipInstallment.status.in_([InstallmentStatus.due, InstallmentStatus.missed]),
            MembershipInstallment.due_date < datetime.now(timezone.utc).date(),
        )
        .first()
    )
    if overdue_remaining is None:
        membership.good_standing = True

    recalculate_stability(
        db=db,
        user_id=membership.user_id,
        program_key=membership.program_key,
    )
    evaluate_member_risk(db=db, membership_id=membership.id)

    db.add(
        AuditLog(
            case_id=None,
            actor_id=None,
            actor_is_ai=False,
            action_type="membership_installment_settled",
            reason_code=f"stripe_invoice_paid_{stripe_invoice_id}",
            before_state={"status": previous_status.value, "stripe_customer_id": stripe_customer_id},
            after_state={
                "status": InstallmentStatus.paid_cash.value,
                "stripe_customer_id": stripe_customer_id,
                "amount_paid_cents": amount_paid_cents,
            },
            policy_version_id=None,
        )
    )

    db.commit()
