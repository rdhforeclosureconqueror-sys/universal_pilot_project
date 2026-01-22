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
        # Step 1: Get or create a policy version
        policy = db.query(PolicyVersion).filter_by(is_active=True).first()
        if not policy:
            policy = PolicyVersion(
                id=uuid.uuid4(),
                program_key="test_program",
                version_tag="v1.0",
                config_json={},
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(policy)
            db.commit()

        # Step 2: Create dummy case
        case_id = uuid.uuid4()
        dummy_case = Case(
            id=case_id,
            status="intake_submitted",
            created_by=uuid.uuid4(),
            created_at=datetime.utcnow(),
            program_type="pilot_program",
            policy_version_id=policy.id
        )
        db.add(dummy_case)
        db.commit()

        # Step 3: Run audit log
        log_audit(
            db=db,
            case_id=case_id,
            actor_id=str(uuid.uuid4()),
            action_type="case_created",
            reason_code="intake_received",
            before_json={},                                # ✅ correct arg name
            after_json={"status": "intake_submitted"},     # ✅ correct arg name
            policy_version_id=policy.id
        )
        db.commit()

        # Step 4: Verify audit log
        logs = db.query(AuditLog).filter_by(case_id=case_id).all()
        assert len(logs) > 0, "❌ No audit log created"
        print("✅ Audit log successfully created:")
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
