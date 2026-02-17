from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from models.audit_logs import AuditLog
from models.cases import Case
from models.documents import Document
from models.enums import CaseStatus
from models.leads import Lead
from models.properties import Property
from models.workflow import (
    CaseWorkflowInstance,
    CaseWorkflowProgress,
    WorkflowOverride,
    WorkflowOverrideCategory,
    WorkflowResponsibleRole,
    WorkflowStep,
    WorkflowStepStatus,
    WorkflowTemplate,
)

FORECLOSURE_PROGRAM_KEY = "foreclosure_stabilization_v1"
MAX_OVERRIDES_PER_CASE = 3

DEFAULT_FORECLOSURE_STEPS: list[dict[str, Any]] = [
    {
        "step_key": "pdf_ingestion",
        "display_name": "PDF Ingestion",
        "responsible_role": WorkflowResponsibleRole.system,
        "required_documents": [],
        "required_actions": ["auction_import_created", "lead_created", "case_created"],
        "blocking_conditions": [],
        "kanban_column": "📥 Lead Ingested",
        "order_index": 1,
        "auto_advance": True,
        "sla_days": 1,
    },
    {
        "step_key": "contact_homeowner",
        "display_name": "Contact Homeowner",
        "responsible_role": WorkflowResponsibleRole.operator,
        "required_documents": [],
        "required_actions": ["contact_attempt_logged", "homeowner_response_logged"],
        "blocking_conditions": ["requires_valid_contact_channel"],
        "kanban_column": "📞 Contact & Qualification",
        "order_index": 2,
        "auto_advance": False,
        "sla_days": 3,
    },
    {
        "step_key": "qualification_review",
        "display_name": "Qualification Review",
        "responsible_role": WorkflowResponsibleRole.operator,
        "required_documents": ["foreclosure_notice", "occupancy_confirmation", "id_verification"],
        "required_actions": ["qualification_review_completed"],
        "blocking_conditions": [],
        "kanban_column": "📄 Intake Complete",
        "order_index": 3,
        "auto_advance": False,
        "sla_days": 5,
    },
    {
        "step_key": "leaseback_execution",
        "display_name": "Leaseback Execution",
        "responsible_role": WorkflowResponsibleRole.operator,
        "required_documents": ["leaseback_signed", "consent_signed"],
        "required_actions": ["leaseback_signed", "consent_signed"],
        "blocking_conditions": [],
        "kanban_column": "⚖️ Stabilization Setup",
        "order_index": 4,
        "auto_advance": True,
        "sla_days": 7,
    },
    {
        "step_key": "stabilization_monitoring",
        "display_name": "Stabilization Monitoring",
        "responsible_role": WorkflowResponsibleRole.operator,
        "required_documents": [],
        "required_actions": ["payment_logs_verified", "compliance_window_met"],
        "blocking_conditions": [],
        "kanban_column": "🏠 Leaseback Active",
        "order_index": 5,
        "auto_advance": False,
        "sla_days": 30,
    },
    {
        "step_key": "rehab_planning",
        "display_name": "Rehab Planning",
        "responsible_role": WorkflowResponsibleRole.operator,
        "required_documents": ["rehab_scope_uploaded"],
        "required_actions": ["rehab_classification_set"],
        "blocking_conditions": [],
        "kanban_column": "🔨 Rehab Planning",
        "order_index": 6,
        "auto_advance": False,
        "sla_days": 14,
    },
    {
        "step_key": "rehab_execution",
        "display_name": "Rehab Execution",
        "responsible_role": WorkflowResponsibleRole.operator,
        "required_documents": [],
        "required_actions": ["milestone_logs_recorded", "contractor_verified", "rehab_completed"],
        "blocking_conditions": [],
        "kanban_column": "🛠 Rehab In Progress",
        "order_index": 7,
        "auto_advance": False,
        "sla_days": 45,
    },
    {
        "step_key": "performance_window",
        "display_name": "Performance Window",
        "responsible_role": WorkflowResponsibleRole.system,
        "required_documents": [],
        "required_actions": ["performance_window_complete"],
        "blocking_conditions": ["compliance_overdue"],
        "kanban_column": "📊 Performance Window",
        "order_index": 8,
        "auto_advance": False,
        "sla_days": 180,
    },
    {
        "step_key": "refinance_ready",
        "display_name": "Refinance Ready",
        "responsible_role": WorkflowResponsibleRole.system,
        "required_documents": ["readiness_packet"],
        "required_actions": [
            "pfdr_ledger_reconciled",
            "shared_equity_active",
            "no_unresolved_flags",
            "documents_complete",
        ],
        "blocking_conditions": [],
        "kanban_column": "💰 Refinance Ready",
        "order_index": 9,
        "auto_advance": False,
        "sla_days": 14,
    },
    {
        "step_key": "completion",
        "display_name": "Completion",
        "responsible_role": WorkflowResponsibleRole.lender,
        "required_documents": [],
        "required_actions": [
            "refinance_completed",
            "shared_equity_extinguished",
            "pfdr_recovered",
            "workflow_completed",
        ],
        "blocking_conditions": [],
        "kanban_column": "🎓 Completed",
        "order_index": 10,
        "auto_advance": False,
        "sla_days": 7,
    },
]


def ensure_default_template(db: Session) -> WorkflowTemplate:
    template = (
        db.query(WorkflowTemplate)
        .filter(WorkflowTemplate.program_key == FORECLOSURE_PROGRAM_KEY)
        .first()
    )
    if template:
        return template

    template = WorkflowTemplate(
        program_key=FORECLOSURE_PROGRAM_KEY,
        name="Foreclosure Stabilization v1",
        template_version=1,
    )
    db.add(template)
    db.flush()

    for step in DEFAULT_FORECLOSURE_STEPS:
        db.add(WorkflowStep(template_id=template.id, **step))

    db.flush()
    return template


def initialize_case_workflow(db: Session, case_id) -> CaseWorkflowInstance:
    template = ensure_default_template(db)

    instance = (
        db.query(CaseWorkflowInstance)
        .filter(CaseWorkflowInstance.case_id == case_id)
        .first()
    )
    if instance:
        return instance

    steps = _ordered_steps(db, template.id)
    first_step = steps[0]

    instance = CaseWorkflowInstance(
        case_id=case_id,
        template_id=template.id,
        locked_template_version=template.template_version,
        current_step_key=first_step.step_key,
    )
    db.add(instance)
    db.flush()

    now = datetime.now(timezone.utc)
    for step in steps:
        progress = CaseWorkflowProgress(
            instance_id=instance.id,
            step_key=step.step_key,
            status=WorkflowStepStatus.pending,
        )
        if step.step_key == first_step.step_key:
            progress.status = WorkflowStepStatus.active
            progress.started_at = now
        db.add(progress)

    db.flush()
    sync_case_workflow(db, case_id)
    return instance


def _ordered_steps(db: Session, template_id):
    return (
        db.query(WorkflowStep)
        .filter(WorkflowStep.template_id == template_id)
        .order_by(WorkflowStep.order_index.asc())
        .all()
    )


def _case_action_set(db: Session, case_id) -> set[str]:
    return {
        row[0]
        for row in db.query(AuditLog.action_type)
        .filter(AuditLog.case_id == case_id)
        .all()
    }


def _case_document_set(db: Session, case_id) -> set[str]:
    return {
        row[0].value if hasattr(row[0], "value") else str(row[0])
        for row in db.query(Document.doc_type)
        .filter(Document.case_id == case_id)
        .all()
    }


def _evaluate_blocking_conditions(conditions: list[str], action_set: set[str]) -> str | None:
    for condition in conditions:
        if condition == "requires_valid_contact_channel" and "valid_contact_channel_verified" not in action_set:
            return "missing_contact_channel"
        if condition == "compliance_overdue" and "compliance_current" not in action_set:
            return "compliance_overdue"
    return None


def evaluate_step_requirements(db: Session, case_id, step: WorkflowStep) -> dict[str, Any]:
    action_set = _case_action_set(db, case_id)
    document_set = _case_document_set(db, case_id)

    required_documents = step.required_documents or []
    required_actions = step.required_actions or []

    missing_documents = [doc for doc in required_documents if doc not in document_set]
    missing_actions = [action for action in required_actions if action not in action_set]

    block_reason = _evaluate_blocking_conditions(step.blocking_conditions or [], action_set)
    if missing_documents:
        block_reason = f"missing_document: {missing_documents[0]}"
    elif missing_actions:
        block_reason = f"missing_action: {missing_actions[0]}"

    return {
        "missing_documents": missing_documents,
        "missing_actions": missing_actions,
        "block_reason": block_reason,
        "is_complete": not missing_documents and not missing_actions and block_reason is None,
    }


def _update_case_status_for_step(db: Session, case: Case, step_key: str):
    if step_key == "leaseback_execution":
        case.status = CaseStatus.in_progress
    elif step_key == "completion":
        case.status = CaseStatus.program_completed_positive_outcome
    db.flush()


def _sla_breached(progress: CaseWorkflowProgress, step: WorkflowStep, now: datetime | None = None) -> bool:
    if progress.status not in (WorkflowStepStatus.active, WorkflowStepStatus.blocked):
        return False
    if not progress.started_at:
        return False
    now = now or datetime.now(timezone.utc)
    return (now - progress.started_at).days > (step.sla_days or 0)


def sync_case_workflow(db: Session, case_id) -> CaseWorkflowInstance | None:
    instance = (
        db.query(CaseWorkflowInstance)
        .filter(CaseWorkflowInstance.case_id == case_id)
        .first()
    )
    if not instance:
        return None

    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == instance.template_id).first()
    if template and instance.locked_template_version != template.template_version:
        # version-lock: do not drift implicitly
        return instance

    steps = _ordered_steps(db, instance.template_id)
    progress_map = {
        p.step_key: p
        for p in db.query(CaseWorkflowProgress)
        .filter(CaseWorkflowProgress.instance_id == instance.id)
        .all()
    }
    now = datetime.now(timezone.utc)

    for i, step in enumerate(steps):
        progress = progress_map[step.step_key]
        if progress.status == WorkflowStepStatus.complete:
            continue

        evaluation = evaluate_step_requirements(db, case_id, step)
        if evaluation["is_complete"]:
            progress.status = WorkflowStepStatus.complete
            progress.block_reason = None
            progress.completed_at = progress.completed_at or now

            next_step = steps[i + 1] if i + 1 < len(steps) else None
            if next_step:
                next_progress = progress_map[next_step.step_key]
                if next_progress.status == WorkflowStepStatus.pending:
                    next_progress.status = WorkflowStepStatus.active
                    next_progress.started_at = next_progress.started_at or now
                    instance.current_step_key = next_step.step_key
                if not step.auto_advance:
                    break
                continue

            instance.completed_at = instance.completed_at or now
            instance.current_step_key = step.step_key
            case = db.query(Case).filter(Case.id == case_id).first()
            if case:
                _update_case_status_for_step(db, case, "completion")
            break

        progress.status = WorkflowStepStatus.blocked if evaluation["block_reason"] else WorkflowStepStatus.active
        progress.block_reason = evaluation["block_reason"]
        instance.current_step_key = step.step_key
        break

    case = db.query(Case).filter(Case.id == case_id).first()
    if case:
        _update_case_status_for_step(db, case, instance.current_step_key)

    db.flush()
    return instance


def get_case_workflow_summary(db: Session, case_id) -> dict[str, Any] | None:
    instance = sync_case_workflow(db, case_id)
    if not instance:
        return None

    steps = _ordered_steps(db, instance.template_id)
    step_map = {s.step_key: s for s in steps}

    progress_rows = (
        db.query(CaseWorkflowProgress)
        .filter(CaseWorkflowProgress.instance_id == instance.id)
        .order_by(CaseWorkflowProgress.started_at.asc().nullslast())
        .all()
    )
    current_step = step_map.get(instance.current_step_key)
    evaluation = evaluate_step_requirements(db, case_id, current_step) if current_step else {
        "missing_documents": [],
        "missing_actions": [],
        "block_reason": None,
    }

    return {
        "current_step": instance.current_step_key,
        "next_required_actions": evaluation["missing_actions"],
        "missing_documents": evaluation["missing_documents"],
        "blocking_conditions": current_step.blocking_conditions if current_step else [],
        "template_version": instance.locked_template_version,
        "timeline_history": [
            {
                "step_key": p.step_key,
                "status": p.status.value,
                "started_at": p.started_at,
                "completed_at": p.completed_at,
                "block_reason": p.block_reason,
                "sla_days": step_map[p.step_key].sla_days if p.step_key in step_map else None,
                "sla_breach": _sla_breached(p, step_map[p.step_key]) if p.step_key in step_map else False,
                "kanban_column": step_map[p.step_key].kanban_column if p.step_key in step_map else None,
            }
            for p in progress_rows
        ],
    }


def get_foreclosure_kanban(db: Session) -> dict[str, Any]:
    template = ensure_default_template(db)
    ordered_steps = _ordered_steps(db, template.id)
    ordered_columns = []
    for step in ordered_steps:
        if step.kanban_column not in ordered_columns:
            ordered_columns.append(step.kanban_column)

    instances = db.query(CaseWorkflowInstance).all()
    column_map: dict[str, list[dict[str, Any]]] = {name: [] for name in ordered_columns}

    for instance in instances:
        case = db.query(Case).filter(Case.id == instance.case_id).first()
        if not case:
            continue

        sync_case_workflow(db, case.id)
        summary = get_case_workflow_summary(db, case.id)
        if not summary:
            continue

        current = next((s for s in summary["timeline_history"] if s["step_key"] == summary["current_step"]), None)
        column_name = current["kanban_column"] if current else "Unmapped"

        prop = db.query(Property).filter(Property.id == case.property_id).first() if case.property_id else None
        lead = None
        if prop:
            lead = (
                db.query(Lead)
                .filter(Lead.address == prop.address, Lead.zip == prop.zip)
                .order_by(Lead.created_at.desc())
                .first()
            )

        days_in_stage = 0
        if current and current["started_at"]:
            days_in_stage = (datetime.now(timezone.utc) - current["started_at"]).days

        case_card = {
            "case_id": str(case.id),
            "homeowner_name": (lead.mortgagor if lead and lead.mortgagor else (prop.mortgagor if prop else None)),
            "address": prop.address if prop else (lead.address if lead else None),
            "days_in_stage": days_in_stage,
            "block_reason": current["block_reason"] if current else None,
            "missing_documents": summary["missing_documents"],
            "next_required_actions": summary["next_required_actions"],
            "compliance_overdue": current["block_reason"] == "compliance_overdue" if current else False,
            "sla_breach": current["sla_breach"] if current else False,
            "blocked": current["status"] == WorkflowStepStatus.blocked.value if current else False,
        }

        column_map.setdefault(column_name, []).append(case_card)

    columns = [
        {
            "name": name,
            "cases": sorted(column_map.get(name, []), key=lambda x: x["days_in_stage"], reverse=True),
        }
        for name in ordered_columns
    ]
    if "Unmapped" in column_map:
        columns.append({"name": "Unmapped", "cases": column_map["Unmapped"]})
    return {"columns": columns}


def apply_workflow_override(
    db: Session,
    case_id,
    to_step_key: str,
    actor_id,
    reason: str,
    reason_category: WorkflowOverrideCategory,
):
    instance = (
        db.query(CaseWorkflowInstance)
        .filter(CaseWorkflowInstance.case_id == case_id)
        .first()
    )
    if not instance:
        return None

    override_count = db.query(WorkflowOverride).filter(WorkflowOverride.case_id == case_id).count()
    if override_count >= MAX_OVERRIDES_PER_CASE:
        return None

    steps = _ordered_steps(db, instance.template_id)
    step_map = {s.step_key: s for s in steps}
    if to_step_key not in step_map:
        return None

    progress_rows = (
        db.query(CaseWorkflowProgress)
        .filter(CaseWorkflowProgress.instance_id == instance.id)
        .all()
    )
    progress_map = {p.step_key: p for p in progress_rows}

    from_step = instance.current_step_key
    target_order = step_map[to_step_key].order_index

    now = datetime.now(timezone.utc)
    for step in steps:
        p = progress_map[step.step_key]
        if step.order_index < target_order:
            p.status = WorkflowStepStatus.complete
            p.completed_at = p.completed_at or now
            p.block_reason = None
            p.started_at = p.started_at or now
        elif step.order_index == target_order:
            p.status = WorkflowStepStatus.active
            p.started_at = p.started_at or now
            p.block_reason = None
            p.completed_at = None
        else:
            p.status = WorkflowStepStatus.pending
            p.started_at = None
            p.completed_at = None
            p.block_reason = None

    instance.current_step_key = to_step_key
    db.add(
        WorkflowOverride(
            case_id=case_id,
            instance_id=instance.id,
            from_step_key=from_step,
            to_step_key=to_step_key,
            reason_category=reason_category,
            reason=reason,
            actor_id=actor_id,
        )
    )
    db.add(
        AuditLog(
            case_id=case_id,
            actor_id=actor_id,
            actor_is_ai=False,
            action_type="workflow_override",
            reason_code="manual_override",
            before_json={"from_step": from_step},
            after_json={"to_step": to_step_key, "reason": reason, "reason_category": reason_category.value},
        )
    )
    db.flush()
    return instance


def get_workflow_analytics(db: Session, default_sla_days: int = 30) -> dict[str, Any]:
    template = ensure_default_template(db)
    step_map = {s.step_key: s for s in _ordered_steps(db, template.id)}

    instances = db.query(CaseWorkflowInstance).all()
    now = datetime.now(timezone.utc)

    stage_durations: dict[str, list[int]] = {}
    blocked_cases = 0
    block_reason_frequency: dict[str, int] = {}
    sla_breach_count = 0
    compliance_delay_count = 0
    time_risk_count = 0
    case_stage_duration: dict[str, int] = {}

    for instance in instances:
        progresses = (
            db.query(CaseWorkflowProgress)
            .filter(CaseWorkflowProgress.instance_id == instance.id)
            .all()
        )
        for p in progresses:
            if not p.started_at:
                continue
            end = p.completed_at or now
            duration = max(0, (end - p.started_at).days)
            stage_durations.setdefault(p.step_key, []).append(duration)

            if p.status in (WorkflowStepStatus.active, WorkflowStepStatus.blocked) and p.step_key == instance.current_step_key:
                case_stage_duration[str(instance.case_id)] = duration

            step = step_map.get(p.step_key)
            step_sla = step.sla_days if step else default_sla_days
            if p.status in (WorkflowStepStatus.active, WorkflowStepStatus.blocked) and duration > step_sla:
                sla_breach_count += 1
                if p.status == WorkflowStepStatus.active:
                    time_risk_count += 1

            if p.status == WorkflowStepStatus.blocked:
                blocked_cases += 1
                reason = p.block_reason or "unknown"
                block_reason_frequency[reason] = block_reason_frequency.get(reason, 0) + 1
                if reason == "compliance_overdue":
                    compliance_delay_count += 1

    override_rows = db.query(WorkflowOverride).all()
    override_by_actor: dict[str, int] = {}
    override_by_category: dict[str, int] = {}
    override_by_case: dict[str, int] = {}
    for r in override_rows:
        aid = str(r.actor_id)
        override_by_actor[aid] = override_by_actor.get(aid, 0) + 1
        cat = r.reason_category.value if hasattr(r.reason_category, "value") else str(r.reason_category)
        override_by_category[cat] = override_by_category.get(cat, 0) + 1
        cid = str(r.case_id)
        override_by_case[cid] = override_by_case.get(cid, 0) + 1

    avg_days_per_stage = {
        step: (sum(vals) / len(vals) if vals else 0)
        for step, vals in stage_durations.items()
    }

    return {
        "case_stage_duration_days": case_stage_duration,
        "portfolio": {
            "case_count": len(instances),
            "avg_days_per_stage": avg_days_per_stage,
            "blocked_case_count": blocked_cases,
            "block_reason_frequency": block_reason_frequency,
            "sla_breach_count": sla_breach_count,
            "time_risk_count": time_risk_count,
            "compliance_delay_count": compliance_delay_count,
            "default_sla_days": default_sla_days,
            "override_count": len(override_rows),
            "override_by_actor": override_by_actor,
            "override_by_category": override_by_category,
            "override_by_case": override_by_case,
        },
    }
