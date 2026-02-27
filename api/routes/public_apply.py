from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from schemas.application import ApplicationCreate
from services.application_service import submit_application


router = APIRouter(tags=["public"])


@router.post("/apply")
def apply(payload: ApplicationCreate, db: Session = Depends(get_db)):
    submit_application(db, payload)
    return {"message": "Application received. Under review."}
