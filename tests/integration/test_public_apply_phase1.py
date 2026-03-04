from uuid import uuid4

from app.models.cases import Case
from app.models.member_layer import Application, Membership, MembershipInstallment, StabilityAssessment
from app.models.users import User
from app.models.workflow import (
    CaseWorkflowInstance,
    WorkflowResponsibleRole,
    WorkflowStep,
    WorkflowTemplate,
)


def _seed_homeowner_template(db):
    template = (
        db.query(WorkflowTemplate)
        .filter(
            WorkflowTemplate.program_key == "homeowner_protection",
            WorkflowTemplate.template_version == 1,
        )
        .first()
    )
    if template:
        return template

    template = WorkflowTemplate(
        id=uuid4(),
        program_key="homeowner_protection",
        name="Homeowner Protection Program",
        template_version=1,
    )
    db.add(template)
    db.flush()

    steps = [
        ("qualification_submitted", "Qualification Submitted", "intake", 1, WorkflowResponsibleRole.operator),
        ("identity_verified", "Identity Verified", "verification", 2, WorkflowResponsibleRole.operator),
        ("property_snapshot", "Property Snapshot", "analysis", 3, WorkflowResponsibleRole.operator),
        ("baseline_stability_generated", "Baseline Stability Generated", "analysis", 4, WorkflowResponsibleRole.system),
        ("plan_activated", "Plan Activated", "activation", 5, WorkflowResponsibleRole.operator),
        ("monthly_checkin_cycle", "Monthly Check-in Cycle", "monitoring", 6, WorkflowResponsibleRole.occupant),
    ]
    for key, name, col, idx, role in steps:
        db.add(
            WorkflowStep(
                id=uuid4(),
                template_id=template.id,
                step_key=key,
                display_name=name,
                responsible_role=role,
                required_documents=[],
                required_actions=[],
                blocking_conditions=[],
                kanban_column=col,
                order_index=idx,
                auto_advance=False,
                sla_days=30,
            )
        )
    db.commit()
    return template


def test_apply_idempotent_activation_flow(client, db_session):
    _seed_homeowner_template(db_session)
    email = f"apply-{uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "full_name": "Apply User",
        "phone": "555-111-2222",
        "program_key": "homeowner_protection",
        "answers_json": {"household_size": 3},
    }

    r1 = client.post("/apply", json=payload)
    assert r1.status_code == 200
    assert r1.json() == {"message": "Application received. Under review."}

    user = db_session.query(User).filter(User.email == email).one()
    apps = db_session.query(Application).filter(Application.email == email).all()
    memberships = db_session.query(Membership).filter(Membership.user_id == user.id).all()
    cases = db_session.query(Case).filter(Case.created_by == user.id, Case.program_key == "homeowner_protection").all()

    assert len(apps) == 1
    assert len(memberships) == 1
    assert len(cases) == 1
    assert (
        db_session.query(MembershipInstallment)
        .filter(MembershipInstallment.membership_id == memberships[0].id)
        .count()
        == 12
    )
    assert (
        db_session.query(CaseWorkflowInstance)
        .filter(CaseWorkflowInstance.case_id == cases[0].id)
        .count()
        == 1
    )
    assert (
        db_session.query(StabilityAssessment)
        .filter(
            StabilityAssessment.user_id == user.id,
            StabilityAssessment.program_key == "homeowner_protection",
        )
        .count()
        == 1
    )

    r2 = client.post("/apply", json=payload)
    assert r2.status_code == 200
    assert r2.json() == {"message": "Application received. Under review."}

    assert db_session.query(Membership).filter(Membership.user_id == user.id).count() == 1
    assert (
        db_session.query(Case)
        .filter(Case.created_by == user.id, Case.program_key == "homeowner_protection")
        .count()
        == 1
    )
