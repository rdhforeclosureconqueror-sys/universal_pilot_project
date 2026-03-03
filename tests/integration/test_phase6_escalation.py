from datetime import date, timedelta
from uuid import uuid4

from app.models.audit_logs import AuditLog
from app.models.member_layer import InstallmentStatus, Membership, MembershipInstallment, MembershipStatus
from app.models.users import User
from app.services.escalation_service import evaluate_member_risk, run_daily_risk_evaluation


def test_evaluate_member_risk_idempotent(db_session):
    user = User(id=uuid4(), email=f"phase6-{uuid4().hex[:6]}@example.com", hashed_password="x")
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

    db_session.add(
        MembershipInstallment(
            id=uuid4(),
            membership_id=membership.id,
            due_date=date.today() - timedelta(days=2),
            amount_cents=1000,
            status=InstallmentStatus.missed,
        )
    )
    db_session.flush()

    first = evaluate_member_risk(db_session, membership.id)
    second = evaluate_member_risk(db_session, membership.id)
    db_session.commit()

    db_session.refresh(membership)
    assert first["risk_triggered"] is True
    assert second["risk_triggered"] is True
    assert membership.good_standing is False
    assert (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action_type == "escalated_due_to_risk",
            AuditLog.reason_code == f"membership:{membership.id}:escalated_due_to_risk",
        )
        .count()
        == 1
    )


def test_run_daily_risk_evaluation(db_session):
    user = User(id=uuid4(), email=f"phase6-daily-{uuid4().hex[:6]}@example.com", hashed_password="x")
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

    db_session.add(
        MembershipInstallment(
            id=uuid4(),
            membership_id=membership.id,
            due_date=date.today() - timedelta(days=1),
            amount_cents=1000,
            status=InstallmentStatus.missed,
        )
    )
    db_session.flush()

    summary = run_daily_risk_evaluation(db_session)
    db_session.commit()

    assert summary["processed_memberships"] >= 1
    assert summary["risk_triggered"] >= 1
