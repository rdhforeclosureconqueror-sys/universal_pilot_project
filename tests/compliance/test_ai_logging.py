from models.ai_activity_logs import AIActivityLog
from helpers.test_helpers import auth_headers, assume_role, create_case, grant_consent, ai_dryrun


def test_ai_dryrun_logs_activity(client, db_session, seeded_user, seeded_policy):
    headers = auth_headers(client)
    case_id = create_case(client)
    assume_role(client, headers, "ai_policy_chair", case_id)

    consent_resp = grant_consent(client, headers, case_id, scope=["ai"])
    assert consent_resp.status_code == 201

    response = ai_dryrun(client, headers, case_id)
    assert response.status_code == 200

    logs = db_session.query(AIActivityLog).filter(AIActivityLog.case_id == case_id).all()
    assert len(logs) == 1
