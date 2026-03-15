from fastapi import APIRouter

from verification.ai_orchestration_integrity_check import verify_ai_orchestration_integrity


router = APIRouter(prefix="/verify", tags=["System Verify"])


@router.get("/ai-orchestration-integrity")
def ai_orchestration_integrity():
    return verify_ai_orchestration_integrity()
