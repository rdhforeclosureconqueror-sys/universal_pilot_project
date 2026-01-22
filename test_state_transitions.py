def test_valid_transitions(client, db_session):
    # intake_submitted → under_review → in_progress → program_completed_positive_outcome
    case_id = create_case(client, "training_sandbox")

    patch_status(client, case_id, "under_review")
    patch_status(client, case_id, "in_progress")
    patch_status(client, case_id, "program_completed_positive_outcome")

    logs = get_audit_logs(db_session, case_id)
    assert any(log.reason_code == "review_approved_start_work" for log in logs)

def test_forbidden_transition(client):
    # intake_submitted → in_progress (should fail)
    case_id = create_case(client, "training_sandbox")
    response = patch_status(client, case_id, "in_progress")

    assert response.status_code in (409, 422)
    assert "forbidden" in response.json()["detail"].lower()
