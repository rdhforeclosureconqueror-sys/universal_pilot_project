def test_ai_dryrun_logs_activity(client, db_session):
    case_id = create_case(client, policy="training_sandbox")
    grant_ai_consent(client, case_id)

    response = client.post("/ai/dryrun", json={
        "case_id": case_id,
        "prompt": "Summarize this case",
        "role": "assistive",
        "policy_rule_id": "doc_summary"
    })

    assert response.status_code == 200
    logs = get_ai_logs(db_session, case_id)
    assert any("prompt_hash" in log for log in logs)
