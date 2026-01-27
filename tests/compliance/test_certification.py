from helpers.test_helpers import create_training_case, submit_quiz, upload_taskcheck_evidence, get_cert_for_user

def test_cert_granted_on_milestone(client, db_session):
    case_id = create_training_case(client)
    submit_quiz(client, case_id, "quiz_universal_flow", correct=True)
    upload_taskcheck_evidence(client, case_id, "create_case_endpoint")
    cert = get_cert_for_user(db_session, user_id="test-user")
    assert cert["status"] == "active"
