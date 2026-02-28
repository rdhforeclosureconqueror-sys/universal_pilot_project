from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.member_layer import Membership, MembershipInstallment, MembershipStatus, InstallmentStatus
from app.models.users import User


def create_membership_with_installments(db: Session, user: User, program_key: str) -> Membership:
    term_start = date.today()
    term_end = term_start + timedelta(days=365)

    membership = Membership(
        user_id=user.id,
        program_key=program_key,
        term_start=term_start,
        term_end=term_end,
        annual_price_cents=12000,
        installment_cents=1000,
        status=MembershipStatus.active,
        good_standing=True,
    )
    db.add(membership)
    db.flush()

    installments = []
    for i in range(12):
        installments.append(
            MembershipInstallment(
                membership_id=membership.id,
                due_date=term_start + timedelta(days=30 * i),
                amount_cents=1000,
                status=InstallmentStatus.due,
            )
        )
    db.add_all(installments)
    return membership
