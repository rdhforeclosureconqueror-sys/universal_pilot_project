from workers.celery_worker import celery_app
from sqlalchemy.orm import Session
from db.session import SessionLocal
from app.models.outbox_queue import OutboxQueue
from app.models.referrals import Referral
from audit.logger import log_audit
from uuid import uuid4
from datetime import datetime

@celery_app.task(bind=True, max_retries=3)
def process_referral_outbox(self, outbox_id: str):
    db: Session = SessionLocal()
    outbox = db.query(OutboxQueue).filter_by(id=outbox_id).first()
    if not outbox:
        return

    if outbox.processed_at is not None:
        return

    # Update status
    outbox.attempts += 1

    try:
        # Example: Mark referral as sent
        payload = outbox.payload
        referral = db.query(Referral).filter_by(id=payload["referral_id"]).first()
        if referral is None:
            raise ValueError("Referral not found for outbox payload")
        if str(referral.status) != "sent":
            referral.status = "sent"
        outbox.processed_at = datetime.utcnow()

        log_audit(
            db=db,
            case_id=referral.case_id,
            actor_id=None,
            actor_is_ai=False,
            action_type="referral_delivered",
            reason_code="referral_sent_success",
            before_state={"status": "queued"},
            after_state={"status": "sent"},
            policy_version_id=None,
        )

        db.commit()

    except Exception as e:
        db.rollback()

        if outbox.attempts >= outbox.max_attempts:
            # Deadletter logic
            log_audit(
                db=db,
                case_id=outbox.case_id,
                actor_id=None,
                actor_is_ai=False,
                action_type="referral_deadlettered",
                reason_code="delivery_failed_max_attempts",
                before_state={},
                after_state={},
                policy_version_id=None
            )
        else:
            self.retry(countdown=2 ** self.request.retries)

        raise e
    finally:
        db.close()
