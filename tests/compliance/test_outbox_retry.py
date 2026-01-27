from helpers.test_helpers import create_outbox_entry, simulate_failure, run_worker, get_outbox_by_id

def test_retry_mechanism(db_session):
    outbox = create_outbox_entry(db_session, attempts=2)
    simulate_failure(outbox)
    run_worker()
    updated = get_outbox_by_id(db_session, outbox.id)
    assert updated.attempts == 3
