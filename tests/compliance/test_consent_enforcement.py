from helpers.test_helpers import auth_headers, assume_role, create_case, queue_referral


def test_referral_blocked_without_consent(client, seeded_user, seeded_policy):
    headers = auth_headers(client)
    case_id = create_case(client)
    assume_role(client, headers, "referral_coordinator", case_id)

    response = queue_referral(client, headers, case_id, partner_id="00000000-0000-0000-0000-000000000001")
    assert response.status_code == 403
