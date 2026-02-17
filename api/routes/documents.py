from datetime import datetime
from uuid import UUID, uuid4
import json

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from audit.logger import log_audit
from auth.dependencies import get_current_user
from db.session import get_db
from models.documents import Document
from models.enums import DocumentType

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/", status_code=201)
def upload_document(
    case_id: UUID = Form(...),
    doc_type: DocumentType = Form(...),
    meta: str = Form("{}"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        meta_json = json.loads(meta)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON in 'meta'") from exc

    if doc_type == DocumentType.other and "evidence_type" not in meta_json:
        raise HTTPException(status_code=422, detail="Missing meta.evidence_type for doc_type='other'")

    # no file_url column in model; keep filename/content_type metadata
    meta_json = {
        **meta_json,
        "filename": file.filename,
        "content_type": file.content_type,
        "uploaded_at": datetime.utcnow().isoformat(),
    }

    doc = Document(
        id=uuid4(),
        case_id=case_id,
        doc_type=doc_type,
        meta=meta_json,
        uploaded_by=user.id,
    )
    db.add(doc)

    log_audit(
        db=db,
        case_id=case_id,
        actor_id=user.id,
        action_type="document_uploaded",
        reason_code=f"upload_{doc_type.value}",
        before_json={},
        after_json={"doc_type": doc_type.value, "filename": file.filename},
    )
    db.commit()
    db.refresh(doc)

    return {"document_id": str(doc.id), "doc_type": doc.doc_type.value}


@router.get("/{doc_id}")
def get_document(doc_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "doc_id": str(doc.id),
        "case_id": str(doc.case_id),
        "doc_type": doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type),
        "meta": doc.meta,
    }


@router.get("/case/{case_id}")
def list_case_documents(case_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    docs = db.query(Document).filter(Document.case_id == case_id).all()
    return [
        {
            "id": str(d.id),
            "doc_type": d.doc_type.value if hasattr(d.doc_type, "value") else str(d.doc_type),
            "meta": d.meta,
        }
        for d in docs
    ]
