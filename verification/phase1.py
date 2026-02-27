from uuid import uuid4

from sqlalchemy.orm import Session

from models.cases import Case
from models.member_layer import Application, Membership, MembershipInstallment, StabilityAssessment
from models.users import User
from models.workflow import (
    CaseWorkflowInstance,
    WorkflowResponsibleRole,
    WorkflowStep,
    WorkflowTemplate,
)
from schemas.application import ApplicationCreate
from services.application_service import submit_application


class Phase1Verifier:
    phase_key = "phase1_intake_activation"

    def verify(self, db: Session, environment: str) -> dict:
        self._ensure_homeowner_template(db)

        email = "verification+phase1@system.local"
        payload = ApplicationCreate(
            email=email,
            full_name="SVF Phase1",
            phone="000-000-0000",
            program_key="homeowner_protection",
            answers_json={"source": "svf", "environment": environment},
        )

        submit_application(db, payload)
        submit_application(db, payload)

        user = db.query(User).filter(User.email == email).first()

        checks = {
            "application_created": db.query(Application).filter(Application.email == email).count() >= 1,
            "user_created": user is not None,
            "membership_created": False,
            "installments_created_12": False,
            "case_created": False,
            "workflow_instance_exists": False,
            "stability_assessment_exists": False,
            "idempotent_membership": False,
            "idempotent_case": False,
        }

        counts = {
            "applications": db.query(Application).filter(Application.email == email).count(),
            "users": 0,
            "memberships": 0,
            "installments": 0,
            "cases": 0,
            "workflow_instances": 0,
            "stability_assessments": 0,
        }

        if user:
            counts["users"] = 1

            membership_count = (
                db.query(Membership)
                .filter(
                    Membership.user_id == user.id,
                    Membership.program_key == payload.program_key,
                )
                .count()
            )
            counts["memberships"] = membership_count
            checks["membership_created"] = membership_count >= 1
            checks["idempotent_membership"] = membership_count == 1

            memberships = (
                db.query(Membership)
                .filter(
                    Membership.user_id == user.id,
                    Membership.program_key == payload.program_key,
                )
                .all()
            )
            if memberships:
                counts["installments"] = (
                    db.query(MembershipInstallment)
                    .filter(MembershipInstallment.membership_id == memberships[0].id)
                    .count()
                )
                checks["installments_created_12"] = counts["installments"] == 12

            case_count = (
                db.query(Case)
                .filter(Case.created_by == user.id, Case.program_key == payload.program_key)
                .count()
            )
            counts["cases"] = case_count
            checks["case_created"] = case_count >= 1
            checks["idempotent_case"] = case_count == 1

            case = (
                db.query(Case)
                .filter(Case.created_by == user.id, Case.program_key == payload.program_key)
                .first()
            )
            if case:
                counts["workflow_instances"] = (
                    db.query(CaseWorkflowInstance)
                    .filter(CaseWorkflowInstance.case_id == case.id)
                    .count()
                )
                checks["workflow_instance_exists"] = counts["workflow_instances"] == 1

            counts["stability_assessments"] = (
                db.query(StabilityAssessment)
                .filter(
                    StabilityAssessment.user_id == user.id,
                    StabilityAssessment.program_key == payload.program_key,
                )
                .count()
            )
            checks["stability_assessment_exists"] = counts["stability_assessments"] >= 1

        success = all(checks.values())
        return {
            "phase_key": self.phase_key,
            "environment": environment,
            "success": success,
            "checks": checks,
            "counts": counts,
        }

    def _ensure_homeowner_template(self, db: Session) -> None:
        template = (
            db.query(WorkflowTemplate)
            .filter(
                WorkflowTemplate.program_key == "homeowner_protection",
                WorkflowTemplate.template_version == 1,
            )
            .first()
        )
        if template:
            return

        template = WorkflowTemplate(
            id=uuid4(),
            program_key="homeowner_protection",
            name="Homeowner Protection Program",
            template_version=1,
        )
        db.add(template)
        db.flush()

        steps = [
            ("qualification_submitted", "Qualification Submitted", WorkflowResponsibleRole.operator, "intake", 1),
            ("identity_verified", "Identity Verified", WorkflowResponsibleRole.operator, "verification", 2),
            ("property_snapshot", "Property Snapshot", WorkflowResponsibleRole.operator, "analysis", 3),
            ("baseline_stability_generated", "Baseline Stability Generated", WorkflowResponsibleRole.system, "analysis", 4),
            ("plan_activated", "Plan Activated", WorkflowResponsibleRole.operator, "activation", 5),
            ("monthly_checkin_cycle", "Monthly Check-in Cycle", WorkflowResponsibleRole.occupant, "monitoring", 6),
        ]

        for step_key, display_name, role, kanban_column, order_index in steps:
            db.add(
                WorkflowStep(
                    id=uuid4(),
                    template_id=template.id,
                    step_key=step_key,
                    display_name=display_name,
                    responsible_role=role,
                    required_documents=[],
                    required_actions=[],
                    blocking_conditions=[],
                    kanban_column=kanban_column,
                    order_index=order_index,
                    auto_advance=False,
                    sla_days=30,
                )
            )
        db.commit()
