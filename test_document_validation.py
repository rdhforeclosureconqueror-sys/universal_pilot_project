def test_invalid_doc_type_other_without_meta(client):
    case_id = create_case(client)
    response = upload_document(client, case_id, doc_type="other", meta={})
    assert response.status_code == 422
