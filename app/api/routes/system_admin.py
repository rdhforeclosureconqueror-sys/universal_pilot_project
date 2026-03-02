from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from verification.engine import VerificationEngine


router = APIRouter(prefix="/admin/system", tags=["system-verification"])


@router.post("/verify/{phase_key}")
def run_phase_verification(phase_key: str, db: Session = Depends(get_db)):
    engine = VerificationEngine(db)
    try:
        return engine.run_phase(phase_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/phases")
def list_phase_statuses(db: Session = Depends(get_db)):
    engine = VerificationEngine(db)
    return engine.list_phase_statuses()
