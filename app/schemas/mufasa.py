from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.users import UserRole
from app.schemas.mufasa import MufasaChatRequest, MufasaChatResponse
from app.services.ai_orchestration_service import handle_mufasa_prompt
from auth.dependencies import get_current_user
from db.session import get_db


router = APIRouter(prefix="/admin/ai/mufasa", tags=["Mufasa AI"])


@router.post("/chat", response_model=MufasaChatResponse)
def mufasa_chat(
    request: MufasaChatRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return handle_mufasa_prompt(
        prompt=request.prompt,
        user_id=user.id,
        db=db,
        investor_mode=request.investor_mode,
    )