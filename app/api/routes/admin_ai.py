from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.schemas.ai_orchestration import AIExecuteRequest, AIMessageRequest, AIVoiceResponse
from app.services.ai_orchestration_service import advisory_message, handle_mufasa_prompt, process_voice
from app.models.users import User, UserRole
from auth.dependencies import require_role
from db.session import get_db
from verification.engine import VerificationEngine


router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])


@router.post(
    "/advisory",
    dependencies=[Depends(require_role([UserRole.admin]))],
)
def ai_advisory(
    request: AIMessageRequest,
    db: Session = Depends(get_db),
):
    return advisory_message(db, request.message)


@router.post(
    "/execute",
    dependencies=[Depends(require_role([UserRole.admin]))],
)
def ai_execute(
    request: AIExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin])),
):
    if request.confirm is not True:
        return {"status": "blocked", "reason": "Execution requires confirm=true"}
    return handle_mufasa_prompt(prompt=request.message, user_id=current_user.id, db=db)


@router.post(
    "/phase7/verify",
    dependencies=[Depends(require_role([UserRole.admin]))],
)
def verify_phase7(
    db: Session = Depends(get_db),
):
    return VerificationEngine(db).run_phase("phase7_ai_orchestration")


@router.post(
    "/voice",
    dependencies=[Depends(require_role([UserRole.admin]))],
    response_model=AIVoiceResponse,
)
async def ai_voice(
    audio: UploadFile = File(...),
    confirm_phrase: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.admin])),
):
    payload = await audio.read()
    return process_voice(db, payload, confirm_phrase, current_user)
