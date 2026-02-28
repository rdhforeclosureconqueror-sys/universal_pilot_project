from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from app.models.leads import Lead

router = APIRouter(prefix="/leads", tags=["leads"])

@router.get("/")
def get_all_leads(db: Session = Depends(get_db)):
    return db.query(Lead).limit(100).all()
