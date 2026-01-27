from helpers.test_helpers import create_case, patch_status, get_audit_logs

def test_valid_transitions(client, db_session):
    case_id = create_case(client)
    patch_status(client, case_id, "under_review")
    patch_status(client, case_id, "in_progress")
    patch_status(client, case_id, "program_completed_positive_outcome")
    logs = get_audit_logs(db_session, case_id)
    assert any(log["reason_code"] == "review_approved_start_work" for log in logs)

def test_forbidden_transition(client):
    case_id = create_case(client)
    response = patch_status(client, case_id, "in_progress")
    assert response.status_code in (409, 422)
