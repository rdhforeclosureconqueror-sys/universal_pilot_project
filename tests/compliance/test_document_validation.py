from helpers.test_helpers import auth_headers, assume_role, create_case, upload_document


def test_invalid_doc_type_other_without_meta(client, seeded_user, seeded_policy):
    headers = auth_headers(client)
    case_id = create_case(client)
    assume_role(client, headers, "case_worker", case_id)

    response = upload_document(client, headers, case_id, doc_type="other", meta={})
    assert response.status_code == 422
