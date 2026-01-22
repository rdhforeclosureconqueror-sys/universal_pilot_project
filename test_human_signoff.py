def test_human_signoff_flag(client, db_session):
    # Verify doc upload marks human_signoff_required=True for taskcheck evidence
    case_id = create_training_case(client)
    upload_taskcheck_evidence(client, case_id, "upload_id_correct_type")

    log = get_audit_log_for_action(db_session, case_id, "taskcheck_completed")
    assert log.meta["human_signoff_required"] is True
