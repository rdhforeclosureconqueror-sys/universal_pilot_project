FORECLOSURE_POLICY_MODULE = {
    "program_key": "foreclosure_assistance",
    "version_tag": "foreclosure_module_v1",
    "config": {
        "review_required": True,
        "dedupe_check": "loan_number",
        "custom_fields": [
            "loan_number",
            "property_address",
            "borrower_name",
        ],
        "required_documents": [
            "foreclosure_notice",
            "id_verification",
            "income_verification",
            "signed_consent",
        ],
    },
}
