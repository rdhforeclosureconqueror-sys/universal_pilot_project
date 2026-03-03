from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.cases import Case
from app.models.workflow import CaseWorkflowInstance, CaseWorkflowProgress, WorkflowStep, WorkflowTemplate, WorkflowStepStatus


def attach_workflow_template(db: Session, case: Case, program_key: str) -> CaseWorkflowInstance:
    existing = db.query(CaseWorkflowInstance).filter(CaseWorkflowInstance.case_id == case.id).first()
    if existing:
        return existing

    template = (
        db.query(WorkflowTemplate)
        .filter(
            WorkflowTemplate.program_key == program_key,
            WorkflowTemplate.template_version == 1,
        )
        .first()
    )
    if not template:
        raise ValueError(f"workflow template not found for program_key={program_key}")

    ordered_steps = (
        db.query(WorkflowStep)
        .filter(WorkflowStep.template_id == template.id)
        .order_by(WorkflowStep.order_index.asc())
        .all()
    )
    if not ordered_steps:
        raise ValueError(f"workflow steps not found for template_id={template.id}")

    instance = CaseWorkflowInstance(
        case_id=case.id,
        template_id=template.id,
        current_step_key=ordered_steps[0].step_key,
        locked_template_version=template.template_version,
    )
    db.add(instance)
    db.flush()

    progresses = []
    for idx, step in enumerate(ordered_steps):
        progresses.append(
            CaseWorkflowProgress(
                instance_id=instance.id,
                step_key=step.step_key,
                status=WorkflowStepStatus.active if idx == 0 else WorkflowStepStatus.pending,
            )
        )
    db.add_all(progresses)
    return instance


def advance_to_risk_stage(db: Session, case_id: UUID) -> bool:
    """Move workflow instance to a risk stage if available; idempotent and no commit."""
    instance = db.query(CaseWorkflowInstance).filter(CaseWorkflowInstance.case_id == case_id).first()
    if not instance:
        return False

    # Prefer an explicit risk stage, fallback to stabilization_monitoring if present.
    available_steps = (
        db.query(WorkflowStep)
        .filter(WorkflowStep.template_id == instance.template_id)
        .all()
    )
    step_keys = {s.step_key for s in available_steps}
    target_step = None
    for candidate in ("risk_escalation", "stabilization_monitoring"):
        if candidate in step_keys:
            target_step = candidate
            break

    if not target_step:
        return False

    if instance.current_step_key == target_step:
        return False

    now = datetime.now(timezone.utc)
    progresses = db.query(CaseWorkflowProgress).filter(CaseWorkflowProgress.instance_id == instance.id).all()
    for progress in progresses:
        if progress.step_key == target_step:
            if progress.status != WorkflowStepStatus.active:
                progress.status = WorkflowStepStatus.active
                if not progress.started_at:
                    progress.started_at = now
        elif progress.status == WorkflowStepStatus.active:
            progress.status = WorkflowStepStatus.complete
            progress.completed_at = now

    instance.current_step_key = target_step
    db.flush()
    return True
