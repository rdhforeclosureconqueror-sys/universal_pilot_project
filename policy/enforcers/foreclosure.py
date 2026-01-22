def validate_foreclosure_checklist(case_id: str, db: Session):
    docs = db.query(Document).filter_by(case_id=case_id).all()
    doc_types = [doc.doc_type for doc in docs]

    required = [
        "foreclosure_notice",
        "id_verification",
        "income_verification",
        "signed_consent"
    ]
    for r in required:
        if r not in doc_types:
            raise HTTPException(status_code=422, detail=f"Missing required document: {r}")
