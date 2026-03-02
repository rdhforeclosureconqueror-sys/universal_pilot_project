from sqlalchemy.orm import Session

from app.models.cases import Case
from app.models.enums import CaseStatus
from app.models.member_layer import Application, Membership, MembershipStatus
from app.models.users import User
from app.services.membership_service import create_membership_with_installments
from app.services.stability_service import create_baseline_stability
from app.services.workflow_service import attach_workflow_template


def activate_member(db: Session, application: Application) -> Membership:
    user = db.query(User).filter(User.email == application.email).first()
    if not user:
        user = User(
            email=application.email,
            full_name=application.full_name,
            hashed_password="!",  # public intake user placeholder
        )
        db.add(user)
        db.flush()

    existing_membership = (
        db.query(Membership)
        .filter(
            Membership.user_id == user.id,
            Membership.program_key == application.program_key,
            Membership.status == MembershipStatus.active,
        )
        .first()
    )
    if existing_membership:
        return existing_membership

    membership = create_membership_with_installments(db, user, application.program_key)

    canonical_key = f"{user.id}:{application.program_key}:{membership.term_start.isoformat()}"
    case = db.query(Case).filter(Case.canonical_key == canonical_key).first()
    if not case:
        case = Case(
            created_by=user.id,
            program_key=application.program_key,
            program_type=application.program_key,
            status=CaseStatus.intake_submitted,
            canonical_key=canonical_key,
            meta={"application_id": str(application.id)},
        )
        db.add(case)
        db.flush()

    attach_workflow_template(db, case, application.program_key)
    create_baseline_stability(db, user, application.program_key)

    return membership
