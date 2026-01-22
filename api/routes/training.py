from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from auth.dependencies import get_current_user
from db.session import get_db
from models.training_quiz_attempts import TrainingQuizAttempt
from models.certifications import Certification
from models.policy_versions import PolicyVersion
from audit.logger import log_audit
from policy.loader import PolicyEngine
from uuid import uuid4
from datetime import datetime

router = APIRouter(prefix="/training", tags=["Training"])

class QuizSubmission(BaseModel):
    case_id: str
    quiz_key: str
    answers: dict

@router.post("/quiz_attempt", status_code=201)
def submit_quiz_attempt(request: QuizSubmission, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Load policy and config
    case = db.query(models.Case).filter_by(id=request.case_id).first()
    if not case or case.case_type != "training_enrollment":
        raise HTTPException(status_code=400, detail="Not a training case")

    policy = PolicyEngine(db).get_policy_by_id(case.policy_version_id).config_json

    quiz_config = next((q for q in policy["required_quizzes"] if q["quiz_key"] == request.quiz_key), None)
    if not quiz_config:
        raise HTTPException(status_code=404, detail="Quiz not found in policy")

    # Evaluate quiz
    correct_count = 0
    for q in quiz_config.get("questions", []):
        if q["prompt"] in request.answers and request.answers[q["prompt"]] == q["correct_answer"]:
            correct_count += 1

    score = correct_count / len(quiz_config.get("questions", []))
    passed = score >= quiz_config["min_pass_score"]

    attempt = TrainingQuizAttempt(
        id=uuid4(),
        user_id=user.id,
        lesson_key=request.quiz_key,
        answers=request.answers,
        passed=passed,
        created_at=datetime.utcnow()
    )
    db.add(attempt)

    log_audit(
        db=db,
        case_id=case.id,
        actor_id=user.id,
        action_type="training_quiz_attempted",
        reason_code="quiz_passed" if passed else "quiz_failed",
        before_state={},
        after_state={"quiz_key": request.quiz_key, "passed": passed},
        policy_version_id=case.policy_version_id
    )

    db.commit()
    return {"passed": passed, "score": round(score, 2)}
