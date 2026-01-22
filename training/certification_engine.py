from sqlalchemy.orm import Session
from models.certifications import Certification
from models.policy_versions import PolicyVersion
from uuid import uuid4
from datetime import datetime

def try_grant_cert(user_id: str, case_id: str, policy_version: PolicyVersion, db: Session):
    config = policy_version.config_json
    for cert in config.get("cert_rules", []):
        cert_key = cert["cert_key"]
        milestone = cert["milestone_key"]
        # Normally you'd check logs or TaskChecks completed — simplified here:
        passed_all = True  # Replace with real milestone check

        if passed_all:
            existing = db.query(Certification).filter_by(user_id=user_id, cert_key=cert_key).first()
            if not existing:
                db.add(Certification(
                    id=uuid4(),
                    user_id=user_id,
                    case_id=case_id,
                    cert_key=cert_key,
                    status="active",
                    issued_at=datetime.utcnow()
                ))
                db.commit()
