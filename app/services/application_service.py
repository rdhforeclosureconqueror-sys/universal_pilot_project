from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.member_layer import Application, ApplicationStatus
from app.schemas.application import ApplicationCreate
from app.services.activation_service import activate_member
from app.services.qualification_service import qualifies


def submit_application(db: Session, payload: ApplicationCreate) -> Application:
    try:
        application = Application(
            email=payload.email,
            full_name=payload.full_name,
            phone=payload.phone,
            program_key=payload.program_key,
            answers_json=payload.answers_json,
            status=ApplicationStatus.submitted,
            submitted_at=datetime.now(timezone.utc),
        )
        db.add(application)
        db.flush()

        if qualifies(application):
            application.status = ApplicationStatus.qualified
            activate_member(db, application)
        else:
            application.status = ApplicationStatus.needs_info

        db.commit()
        db.refresh(application)
        return application
    except Exception:
        db.rollback()
        raise
