from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.schemas.member_dashboard import InstallmentDTO, MemberDashboardDTO, WorkflowStepDTO
from models.cases import Case
from models.member_layer import InstallmentStatus, Membership, MembershipStatus, MembershipInstallment, StabilityAssessment
from models.workflow import CaseWorkflowInstance, CaseWorkflowProgress, WorkflowStep, WorkflowStepStatus


def get_member_dashboard(db: Session, user_id: UUID) -> MemberDashboardDTO:
    membership = (
        db.query(Membership)
        .filter(
            Membership.user_id == user_id,
            Membership.status == MembershipStatus.active,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Active membership not found")

    latest_stability = (
        db.query(StabilityAssessment)
        .filter(
            StabilityAssessment.user_id == user_id,
            StabilityAssessment.program_key == membership.program_key,
        )
        .order_by(StabilityAssessment.created_at.desc())
        .first()
    )

    next_due_installment_row = (
        db.query(MembershipInstallment)
        .filter(
            MembershipInstallment.membership_id == membership.id,
            MembershipInstallment.status == InstallmentStatus.due,
        )
        .order_by(MembershipInstallment.due_date.asc())
        .first()
    )

    next_due_installment = None
    if next_due_installment_row:
        next_due_installment = InstallmentDTO(
            due_date=next_due_installment_row.due_date,
            amount_cents=next_due_installment_row.amount_cents,
            status=next_due_installment_row.status.value
            if hasattr(next_due_installment_row.status, "value")
            else str(next_due_installment_row.status),
        )

    latest_case = (
        db.query(Case)
        .filter(
            Case.created_by == user_id,
            Case.program_key == membership.program_key,
        )
        .order_by(Case.created_at.desc())
        .first()
    )

    next_step = None
    if latest_case:
        workflow_instance = (
            db.query(CaseWorkflowInstance)
            .filter(CaseWorkflowInstance.case_id == latest_case.id)
            .first()
        )
        if workflow_instance:
            incomplete_statuses = [
                WorkflowStepStatus.pending,
                WorkflowStepStatus.active,
                WorkflowStepStatus.blocked,
            ]
            next_step_row = (
                db.query(CaseWorkflowProgress, WorkflowStep)
                .join(
                    WorkflowStep,
                    (WorkflowStep.template_id == workflow_instance.template_id)
                    & (WorkflowStep.step_key == CaseWorkflowProgress.step_key),
                )
                .filter(
                    CaseWorkflowProgress.instance_id == workflow_instance.id,
                    CaseWorkflowProgress.status.in_(incomplete_statuses),
                )
                .order_by(WorkflowStep.order_index.asc())
                .first()
            )
            if next_step_row:
                progress, step = next_step_row
                next_step = WorkflowStepDTO(
                    step_key=progress.step_key,
                    label=step.display_name,
                )

    return MemberDashboardDTO(
        membership_status=membership.status.value if hasattr(membership.status, "value") else str(membership.status),
        good_standing=membership.good_standing,
        stability_score=latest_stability.stability_score if latest_stability else 70,
        risk_level=latest_stability.risk_level if latest_stability else None,
        next_workflow_step=next_step,
        next_installment=next_due_installment,
    )
