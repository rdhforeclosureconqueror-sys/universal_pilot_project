from datetime import date, timedelta
from uuid import uuid4

from app.models.member_layer import (
    InstallmentStatus,
    Membership,
    MembershipInstallment,
    MembershipStatus,
    StabilityAssessment,
)
from app.models.users import User
from app.services.admin_dashboard_service import (
    get_membership_detail,
    list_memberships,
    memberships_below_stability,
    memberships_with_missed_installments,
)


def test_admin_dashboard_queries(db_session):
    user = User(id=uuid4(), email=f"phase4-{uuid4().hex[:6]}@example.com", hashed_password="x")
    db_session.add(user)
    db_session.flush()

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
    db_session.add(membership)
    db_session.flush()

    db_session.add_all(
        [
            MembershipInstallment(
                id=uuid4(),
                membership_id=membership.id,
                due_date=date.today(),
                amount_cents=1000,
                status=InstallmentStatus.missed,
            ),
            MembershipInstallment(
                id=uuid4(),
                membership_id=membership.id,
                due_date=date.today() + timedelta(days=30),
                amount_cents=1000,
                status=InstallmentStatus.due,
            ),
        ]
    )

    db_session.add_all(
        [
            StabilityAssessment(
                id=uuid4(),
                user_id=user.id,
                program_key="homeowner_protection",
                stability_score=70,
                breakdown_json={"baseline": 70},
            ),
            StabilityAssessment(
                id=uuid4(),
                user_id=user.id,
                program_key="homeowner_protection",
                stability_score=60,
                breakdown_json={"baseline": 60},
            ),
        ]
    )
    db_session.commit()

    listed = list_memberships(db_session, program_key="homeowner_protection")
    assert listed.items

    below = memberships_below_stability(db_session, threshold=65, program_key="homeowner_protection")
    assert below.items

    missed = memberships_with_missed_installments(db_session, program_key="homeowner_protection")
    assert missed.items

    detail = get_membership_detail(db_session, membership.id)
    assert detail.installments
    assert detail.stability_history
