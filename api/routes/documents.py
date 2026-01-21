from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from models.documents import Document, DocumentType
from models.audit_logs import AuditLog
from db.session import get_db
from auth.dependencies import get_current_user
from uuid import uuid4
from datetime import datetime
import json

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/", status_code=201)
def upload_document(
    case_id: str = Form(...),
    doc_type: DocumentType = Form(...),
    meta: str = Form("{}"),  # Default to empty JSON string
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        meta_json = json.loads(meta)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in 'meta'")

    # Enforce 'evidence_type' if doc_type is 'other'
    if doc_type == DocumentType.other:
        if "evidence_type" not in meta_json:
            raise HTTPException(
                status_code=422,
                detail="Missing meta.evidence_type for doc_type='other'"
            )
    else:
        meta_json = {}

    doc = Document(
        id=uuid4(),
        case_id=case_id,
        doc_type=doc_type,
        meta=meta_json,
        uploaded_by=user.id,
        file_url=f"s3://your-bucket/{file.filename}"  # Replace with actual S3 logic
    )
    db.add(doc)

    audit = AuditLog(
        id=uuid4(),
        case_id=case_id,
        actor_id=user.id,
        action_type="document_uploaded",
        reason_code=f"upload_{doc_type}",
        before_state={},
        after_state={"doc_type": doc_type},
        created_at=datetime.utcnow()
    )
    db.add(audit)
    db.commit()

    return {"document_id": doc.id, "doc_type": doc.doc_type}


@router.get("/{doc_id}")
def get_document(doc_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "doc_id": doc.id,
        "case_id": doc.case_id,
        "doc_type": doc.doc_type,
        "meta": doc.meta,
        "file_url": doc.file_url
    }


@router.get("/case/{case_id}")
def list_case_documents(case_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    docs = db.query(Document).filter(Document.case_id == case_id).all()
    return [{"id": d.id, "doc_type": d.doc_type, "meta": d.meta} for d in docs]
