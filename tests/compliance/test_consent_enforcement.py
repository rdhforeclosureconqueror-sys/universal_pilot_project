from helpers.test_helpers import create_case, queue_referral

def test_referral_blocked_without_consent(client):
    case_id = create_case(client)
    response = queue_referral(client, case_id, partner_id="1234")
    assert response.status_code == 403
