from db.session import SessionLocal
from models.cases import Case
from models.policy_versions import PolicyVersion
from models.audit_logs import AuditLog
from audit.logger import log_audit
import uuid
from datetime import datetime

def run_audit_test():
    db = SessionLocal()

    try:
        # Create dummy case
        case_id = str(uuid.uuid4())
        policy = db.query(PolicyVersion).filter_by(is_active=True).first()
        
        dummy_case = Case(
            id=case_id,
            status="intake_submitted",
            policy_version_id=policy.id if policy else None,
            created_at=datetime.utcnow()
        )
        db.add(dummy_case)
        db.commit()

        # Run audit log
        log_audit(
            db=db,
            case_id=case_id,
            actor_id="test_user_123",
            action_type="case_created",
            reason_code="intake_received",
            before_state={},
            after_state={"status": "intake_submitted"},
            policy_version_id=policy.id if policy else None
        )
        db.commit()

        # Query audit log
        logs = db.query(AuditLog).filter_by(case_id=case_id).all()
        assert len(logs) > 0, "No audit log created"
        print("✅ Audit log created:")
        for log in logs:
            print({
                "action": log.action_type,
                "reason": log.reason_code,
                "created_at": log.created_at.isoformat()
            })

    except Exception as e:
        print("❌ ERROR:", e)

    finally:
        db.close()

if __name__ == "__main__":
    run_audit_test()
