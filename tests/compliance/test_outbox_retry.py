from datetime import datetime
from uuid import uuid4

from models.outbox_queue import OutboxQueue
from workers.tasks.referral_delivery import process_referral_outbox


def test_retry_skips_already_processed(db_session):
    outbox = OutboxQueue(
        id=uuid4(),
        event_type="send_referral",
        case_id=uuid4(),
        payload={"referral_id": str(uuid4())},
        dedupe_key=f"k-{uuid4().hex}",
        attempts=1,
        max_attempts=3,
        processed_at=datetime.utcnow(),
    )
    db_session.add(outbox)
    db_session.commit()

    process_referral_outbox(str(outbox.id))
    db_session.refresh(outbox)
    assert outbox.attempts == 1
