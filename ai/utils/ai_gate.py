from fastapi import HTTPException
from app.models.consent_records import ConsentRecord
from app.models.policy_versions import PolicyVersion

def check_ai_consent(case_id: str, db):
    consent = db.query(ConsentRecord).filter(
        ConsentRecord.case_id == case_id,
        ConsentRecord.revoked == False,
        ConsentRecord.scope.contains(["ai"])
    ).first()

    if not consent:
        raise HTTPException(status_code=403, detail="AI consent not granted for this case")

def is_ai_disabled(policy: PolicyVersion, role: str):
    ai_settings = policy.config_json.get("ai_settings", {})
    return (
        ai_settings.get("ai_kill_switch_enabled") is True or
        ai_settings.get(f"disable_{role}", False)
    )
