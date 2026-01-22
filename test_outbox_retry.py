def test_retry_mechanism(db_session):
    outbox = create_outbox_entry(db_session, attempts=2)
    simulate_failure(outbox)
    run_worker()
    updated = get_outbox_by_id(db_session, outbox.id)

    assert updated.attempts == 3
    assert updated.processed_at is not None or updated.failed
