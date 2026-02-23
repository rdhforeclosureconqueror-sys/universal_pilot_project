from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ingestion.dallas.db_writer import write_to_db
from models.audit_logs import AuditLog
from models.base import Base
from models.cases import Case
from models.documents import Document
from models.enums import CaseStatus, DocumentType
from models.properties import Property
from models.workflow import (
    CaseWorkflowInstance,
    CaseWorkflowProgress,
    WorkflowOverrideCategory,
    WorkflowStepStatus,
)
from services.workflow_engine import (
    apply_workflow_override,
    get_workflow_analytics,
    initialize_case_workflow,
    sync_case_workflow,
)


def _session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


def test_duplicate_ingestion_replay_idempotent_case_creation():
    db = _session()
    rec = {
        "external_id": "ext-1",
        "address": "123 Main St",
        "city": "Dallas",
        "state": "TX",
        "zip": "75201",
        "county": "Dallas",
        "mortgagor": "Jane Doe",
        "mortgagee": "Bank",
        "trustee": "Trustee",
        "auction_date": datetime.now(timezone.utc),
        "source": "dallas_county_pdf",
        "status": "auction_intake",
        "case_number": "CASE1",
    }

    write_to_db(rec, db)
    write_to_db(rec, db)
    db.commit()

    assert db.query(Property).count() == 1
    assert db.query(Case).count() == 1


def test_workflow_auto_advance_from_ingestion_step():
    db = _session()
    case = Case(
        id=uuid4(),
        status=CaseStatus.auction_intake,
        created_by=uuid4(),
        program_type="FORECLOSURE_PREVENTION",
        program_key="foreclosure_stabilization_v1",
        auction_date=datetime.now(timezone.utc),
        canonical_key="k1",
    )
    db.add(case)
    db.add_all([
        AuditLog(id=uuid4(), case_id=case.id, actor_id=None, action_type="auction_import_created", reason_code="x"),
        AuditLog(id=uuid4(), case_id=case.id, actor_id=None, action_type="lead_created", reason_code="x"),
        AuditLog(id=uuid4(), case_id=case.id, actor_id=None, action_type="case_created", reason_code="x"),
    ])
    db.flush()

    initialize_case_workflow(db, case.id)
    sync_case_workflow(db, case.id)
    inst = db.query(CaseWorkflowInstance).filter_by(case_id=case.id).first()
    assert inst.current_step_key == "contact_homeowner"


def test_override_application_and_limits():
    db = _session()
    case = Case(
        id=uuid4(),
        status=CaseStatus.auction_intake,
        created_by=uuid4(),
        program_type="FORECLOSURE_PREVENTION",
        program_key="foreclosure_stabilization_v1",
        auction_date=datetime.now(timezone.utc),
        canonical_key="k2",
    )
    db.add(case)
    db.flush()
    initialize_case_workflow(db, case.id)

    actor = uuid4()
    for i in range(3):
        assert apply_workflow_override(
            db,
            case.id,
            "qualification_review",
            actor,
            f"reason-{i}",
            WorkflowOverrideCategory.system_recovery,
        ) is not None
    # 4th should be denied by max frequency
    assert apply_workflow_override(
        db,
        case.id,
        "qualification_review",
        actor,
        "reason-4",
        WorkflowOverrideCategory.system_recovery,
    ) is None


def test_sla_breach_conditions_time_based_vs_blocked():
    db = _session()
    case = Case(
        id=uuid4(),
        status=CaseStatus.auction_intake,
        created_by=uuid4(),
        program_type="FORECLOSURE_PREVENTION",
        program_key="foreclosure_stabilization_v1",
        auction_date=datetime.now(timezone.utc),
        canonical_key="k3",
    )
    db.add(case)
    db.flush()
    initialize_case_workflow(db, case.id)
    inst = db.query(CaseWorkflowInstance).filter_by(case_id=case.id).first()
    prog = db.query(CaseWorkflowProgress).filter_by(instance_id=inst.id, step_key="pdf_ingestion").first()
    prog.started_at = datetime.now(timezone.utc) - timedelta(days=3)
    prog.status = WorkflowStepStatus.active
    db.flush()

    analytics = get_workflow_analytics(db, default_sla_days=1)
    assert analytics["portfolio"]["sla_breach_count"] >= 1


def test_canonical_key_uniqueness_enforced_app_level():
    db = _session()
    c1 = Case(
        id=uuid4(),
        status=CaseStatus.auction_intake,
        created_by=uuid4(),
        canonical_key="dup-key",
        program_key="foreclosure_stabilization_v1",
    )
    db.add(c1)
    db.commit()

    c2 = Case(
        id=uuid4(),
        status=CaseStatus.auction_intake,
        created_by=uuid4(),
        canonical_key="dup-key",
        program_key="foreclosure_stabilization_v1",
    )
    db.add(c2)
    raised = False
    try:
        db.commit()
    except Exception:
        raised = True
        db.rollback()
    assert raised
