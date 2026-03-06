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


from uuid import UUID, uuid4
from app.models.audit_logs import AuditLog
from app.models.housing_intelligence import MembershipProfile


def create_membership(db: Session, *, user_id: UUID, case_id: UUID | None, membership_type: str, actor_id: UUID | None) -> MembershipProfile:
    profile = MembershipProfile(
        user_id=user_id,
        case_id=case_id,
        membership_status="active",
        membership_type=membership_type,
        equity_share=0.0,
        voting_power=1.0,
        join_date=date.today(),
    )
    db.add(profile)
    db.flush()

    db.add(
        AuditLog(
            id=uuid4(),
            case_id=case_id,
            actor_id=actor_id,
            actor_is_ai=False,
            action_type="membership_created",
            reason_code="membership_profile_created",
            before_state={},
            after_state={"membership_profile_id": str(profile.id), "membership_type": membership_type},
            policy_version_id=None,
        )
    )

    return profile


def update_membership_status(db: Session, *, membership_profile_id: UUID, membership_status: str, actor_id: UUID | None) -> MembershipProfile | None:
    profile = db.query(MembershipProfile).filter(MembershipProfile.id == membership_profile_id).first()
    if not profile:
        return None
    before = profile.membership_status
    profile.membership_status = membership_status
    db.flush()

    db.add(
        AuditLog(
            id=uuid4(),
            case_id=profile.case_id,
            actor_id=actor_id,
            actor_is_ai=False,
            action_type="membership_status_updated",
            reason_code="membership_profile_status_updated",
            before_state={"membership_status": before},
            after_state={"membership_status": membership_status},
            policy_version_id=None,
        )
    )

    return profile


def calculate_member_equity(db: Session, *, membership_profile_id: UUID) -> dict:
    profile = db.query(MembershipProfile).filter(MembershipProfile.id == membership_profile_id).first()
    if not profile:
        return {"error": "membership_profile_not_found"}

    equity_value = round(float(profile.equity_share or 0) * 1000, 2)
    return {
        "membership_profile_id": str(profile.id),
        "equity_share": float(profile.equity_share or 0),
        "equity_value": equity_value,
        "voting_power": float(profile.voting_power or 0),
    }
