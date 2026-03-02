import hashlib
import hmac
import json
from datetime import date, timedelta
from uuid import uuid4

from app.models.audit_logs import AuditLog
from app.models.member_layer import InstallmentStatus, Membership, MembershipInstallment, MembershipStatus, StabilityAssessment
from app.models.users import User


def _stripe_sig(secret: str, payload: bytes, timestamp: str = "1700000000") -> str:
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_stripe_webhook_settlement_idempotent(client, db_session, monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    user = User(id=uuid4(), email=f"phase5-{uuid4().hex[:6]}@example.com", hashed_password="x")
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
        good_standing=False,
    )
    db_session.add(membership)
    db_session.flush()

    installment = MembershipInstallment(
        id=uuid4(),
        membership_id=membership.id,
        due_date=date.today(),
        amount_cents=1000,
        status=InstallmentStatus.due,
        stripe_invoice_id="in_test_123",
    )
    db_session.add(installment)
    db_session.add(
        StabilityAssessment(
            id=uuid4(),
            user_id=user.id,
            property_id=None,
            program_key="homeowner_protection",
            stability_score=70,
            risk_level=None,
            breakdown_json={"baseline": 70},
        )
    )
    db_session.commit()

    payload = {
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_test_123",
                "customer": "cus_test_123",
                "amount_paid": 1000,
            }
        },
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {"Stripe-Signature": _stripe_sig("whsec_test", body)}

    r1 = client.post("/webhooks/stripe", data=body, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["status"] == "ok"

    db_session.refresh(installment)
    db_session.refresh(membership)
    assert installment.status == InstallmentStatus.paid_cash
    assert installment.paid_at is not None
    assert installment.amount_paid_cents == 1000
    assert membership.good_standing is True

    stability_rows = (
        db_session.query(StabilityAssessment)
        .filter(
            StabilityAssessment.user_id == user.id,
            StabilityAssessment.program_key == "homeowner_protection",
        )
        .order_by(StabilityAssessment.created_at.asc())
        .all()
    )
    assert len(stability_rows) == 2
    assert stability_rows[-1].stability_score > stability_rows[0].stability_score

    audit_after_first = db_session.query(AuditLog).filter(AuditLog.reason_code == "stripe_invoice_paid_in_test_123").count()
    assert audit_after_first == 1

    r2 = client.post("/webhooks/stripe", data=body, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["status"] == "ok"

    assert (
        db_session.query(StabilityAssessment)
        .filter(
            StabilityAssessment.user_id == user.id,
            StabilityAssessment.program_key == "homeowner_protection",
        )
        .count()
        == 2
    )
    assert db_session.query(AuditLog).filter(AuditLog.reason_code == "stripe_invoice_paid_in_test_123").count() == 1
