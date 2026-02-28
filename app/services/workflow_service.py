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
