from models.ai_activity_logs import AIActivityLog
from uuid import uuid4
from datetime import datetime

def log_ai_activity(
    db,
    case_id: str,
    policy_version_id: str,
    ai_role: str,
    model_provider: str,
    model_name: str,
    model_version: str,
    prompt_hash: str,
    policy_rule_id: str,
    confidence_score: float,
    human_override: bool = False,
    incident_type: str = None,
    admin_review_required: bool = False,
    resolved_at=None
):
    db.add(AIActivityLog(
        id=str(uuid4()),
        case_id=case_id,
        policy_version_id=policy_version_id,
        ai_role=ai_role,
        model_provider=model_provider,
        model_name=model_name,
        model_version=model_version,
        prompt_hash=prompt_hash,
        policy_rule_id=policy_rule_id,
        confidence_score=confidence_score,
        human_override=human_override,
        incident_type=incident_type,
        admin_review_required=admin_review_required,
        resolved_at=resolved_at,
        created_at=datetime.utcnow()
    ))
