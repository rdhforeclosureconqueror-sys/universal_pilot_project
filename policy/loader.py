from sqlalchemy.orm import Session
from models.policy_versions import PolicyVersion
from fastapi import HTTPException

class PolicyEngine:
    def __init__(self, db: Session):
        self.db = db

    def get_active_policy(self, program_key: str) -> PolicyVersion:
        policy = self.db.query(PolicyVersion).filter_by(
            program_key=program_key,
            is_active=True
        ).order_by(PolicyVersion.created_at.desc()).first()

        if not policy:
            raise HTTPException(status_code=404, detail="Active policy not found")

        return policy

    def get_policy_by_id(self, policy_version_id: str) -> PolicyVersion:
        policy = self.db.query(PolicyVersion).filter_by(id=policy_version_id).first()

        if not policy:
            raise HTTPException(status_code=404, detail="Policy version not found")

        return policy

    def get_config_json(self, policy_version_id: str) -> dict:
        policy = self.get_policy_by_id(policy_version_id)
        return policy.config_json or {}
