from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ai.diamond_ai_model_adapter import AIModelAdapter
from ai.logger import log_ai_activity
from ai.utils.ai_gate import check_ai_consent, is_ai_disabled
from db.session import get_db
from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from audit.logger import log_audit
from policy.loader import PolicyEngine
from models.cases import Case
import hashlib

router = APIRouter(prefix="/ai", tags=["Diamond AI"])


class AIRequest(BaseModel):
    case_id: str
    prompt: str
    role: str  # assistive, advisory, automated
    policy_rule_id: str


@router.post("/dryrun")
def ai_dryrun(request: AIRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=request.case_id, action="ai.dryrun")

    case = db.query(Case).filter_by(id=request.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    check_ai_consent(case.id, db)

    policy = PolicyEngine(db).get_policy_by_id(case.policy_version_id)
    if is_ai_disabled(policy, request.role):
        raise HTTPException(status_code=403, detail="AI disabled by policy")

    adapter = AIModelAdapter("local", "stubbed", "v1")
    result = adapter.run_inference(request.prompt, context={"system_message": "You are an assistant."})
    prompt_hash = hashlib.sha256(request.prompt.encode()).hexdigest()

    log_ai_activity(
        db=db,
        case_id=case.id,
        policy_version_id=case.policy_version_id,
        ai_role=request.role,
        model_provider="local",
        model_name="stubbed",
        model_version="v1",
        prompt_hash=prompt_hash,
        policy_rule_id=request.policy_rule_id,
        confidence_score=0.9
    )

    log_audit(
        db=db,
        case_id=case.id,
        actor_id=user.id,
        actor_is_ai=True,
        action_type="ai_dryrun_previewed",
        reason_code="ai_suggestion_generated",
        before_state={},
        after_state={"prompt_hash": prompt_hash},
        policy_version_id=case.policy_version_id
    )

    db.commit()
    return {
        "output": result["output"],
        "prompt_hash": prompt_hash,
        "model": "local-v1"
    }
