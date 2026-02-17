from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from models.cases import Case
from services.workflow_engine import (
    get_case_workflow_summary,
    get_foreclosure_kanban,
    initialize_case_workflow,
    sync_case_workflow,
)

router = APIRouter(tags=["Workflow"])


@router.get("/kanban/foreclosure")
def foreclosure_kanban(db: Session = Depends(get_db)):
    payload = get_foreclosure_kanban(db)
    db.commit()
    return payload


@router.get("/cases/{case_id}/workflow")
def case_workflow(case_id: UUID, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    initialize_case_workflow(db, case.id)
    sync_case_workflow(db, case.id)
    summary = get_case_workflow_summary(db, case.id)
    db.commit()
    return summary
