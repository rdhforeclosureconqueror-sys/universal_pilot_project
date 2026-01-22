def test_cert_granted_on_milestone(client, db_session):
    # Complete all required taskchecks
    case_id = create_training_case(client)
    submit_quiz(client, case_id, "quiz_universal_flow", correct=True)
    upload_taskcheck_evidence(client, case_id, "create_case_endpoint")

    cert = get_cert_for_user(db_session, user_id)
    assert cert.status == "active"
