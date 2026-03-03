from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import require_role
from sqlalchemy.orm import Session

from db.session import get_db
from app.models.cases import Case
from app.models.documents import Document
from app.models.users import UserRole
from app.services.workflow_engine import get_case_workflow_summary, initialize_case_workflow, sync_case_workflow

router = APIRouter(prefix="/partner/v1", tags=["Partner API"])


@router.get("/cases/{case_id}/status")
def partner_case_status(
    case_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_role([UserRole.partner_org, UserRole.admin, UserRole.audit_steward])),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return {
        "case_id": str(case.id),
        "status": case.status.value if hasattr(case.status, "value") else str(case.status),
        "program_key": case.program_key,
        "auction_date": case.auction_date,
    }


@router.get("/cases/{case_id}/workflow-readiness")
def partner_workflow_readiness(
    case_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_role([UserRole.partner_org, UserRole.admin, UserRole.audit_steward])),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    initialize_case_workflow(db, case.id)
    sync_case_workflow(db, case.id)
    summary = get_case_workflow_summary(db, case.id)
    db.commit()
    return {
        "case_id": str(case.id),
        "current_step": summary["current_step"],
        "next_required_actions": summary["next_required_actions"],
        "missing_documents": summary["missing_documents"],
        "timeline_history": summary["timeline_history"],
    }


@router.get("/cases/{case_id}/evidence-verification")
def partner_evidence_verification(
    case_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_role([UserRole.partner_org, UserRole.admin, UserRole.audit_steward])),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    docs = db.query(Document).filter(Document.case_id == case.id).all()
    return {
        "case_id": str(case.id),
        "documents": [
            {
                "doc_type": d.doc_type.value if hasattr(d.doc_type, "value") else str(d.doc_type),
                "uploaded_at": d.uploaded_at,
                "meta": d.meta,
            }
            for d in docs
        ],
    }
