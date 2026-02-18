from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.dependencies import require_role
from db.session import get_db
from models.cases import Case
from models.users import UserRole
from models.workflow import WorkflowOverrideCategory
from services.workflow_engine import (
    apply_workflow_override,
    get_case_workflow_summary,
    get_foreclosure_kanban,
    get_workflow_analytics,
    initialize_case_workflow,
    sync_case_workflow,
)

router = APIRouter(tags=["Workflow"])


@router.get("/kanban/foreclosure")
def foreclosure_kanban(db: Session = Depends(get_db)):
    payload = get_foreclosure_kanban(db)
    db.commit()
    return payload


@router.get("/workflow/analytics/foreclosure")
@router.get("/workflow/analytics/foreclosure")
def foreclosure_workflow_analytics(
    sla_days: int = 30,
    db: Session = Depends(get_db),
):
    payload = get_workflow_analytics(db=db, sla_days=sla_days)
    db.commit()
    return payload


@router.get("/workflow/reports/stage-distribution")
def report_stage_distribution(db: Session = Depends(get_db)):
    kanban = get_foreclosure_kanban(db)
    payload = {
        "stage_distribution": [
            {"stage": c["name"], "count": len(c["cases"])}
            for c in kanban["columns"]
        ]
    }
    db.commit()
    return payload


@router.get("/workflow/reports/time-per-stage")
def report_time_per_stage(db: Session = Depends(get_db)):
    analytics = get_workflow_analytics(db)
    payload = {
        "avg_days_per_stage": analytics["portfolio"]["avg_days_per_stage"]
    }
    db.commit()
    return payload


@router.get("/workflow/reports/block-reasons")
def report_block_reasons(db: Session = Depends(get_db)):
    analytics = get_workflow_analytics(db)
    payload = {
        "block_reason_frequency": analytics["portfolio"]["block_reason_frequency"]
    }
    db.commit()
    return payload


@router.get("/workflow/reports/sla-breaches")
def report_sla_breaches(db: Session = Depends(get_db)):
    analytics = get_workflow_analytics(db)
    payload = {
        "sla_breach_count": analytics["portfolio"]["sla_breach_count"],
        "time_risk_count": analytics["portfolio"]["time_risk_count"],
    }
    db.commit()
    return payload


@router.get("/workflow/reports/refinance-ready")
def report_refinance_ready(db: Session = Depends(get_db)):
    kanban = get_foreclosure_kanban(db)
    ready = next(
        (c for c in kanban["columns"] if c["name"] == "💰 Refinance Ready"),
        {"cases": []},
    )
    payload = {
        "refinance_ready_count": len(ready["cases"]),
        "cases": ready["cases"],
    }
    db.commit()
    return payload

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


@router.post("/cases/{case_id}/workflow/override")
def workflow_override(
    case_id: UUID,
    to_step_key: str,
    reason: str,
    reason_category: WorkflowOverrideCategory,
    db: Session = Depends(get_db),
    user=Depends(require_role([UserRole.admin, UserRole.audit_steward])),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    initialize_case_workflow(db, case.id)
    result = apply_workflow_override(
        db=db,
        case_id=case.id,
        to_step_key=to_step_key,
        actor_id=user.id,
        reason=reason,
        reason_category=reason_category,
    
    )
    if not result:
        raise HTTPException(status_code=400, detail="Invalid workflow override target")

    sync_case_workflow(db, case.id)
    summary = get_case_workflow_summary(db, case.id)
    db.commit()
    return summary
