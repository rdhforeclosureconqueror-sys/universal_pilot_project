from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.payment_service import mark_installment_paid
from auth.dependencies import get_current_user
from db.session import get_db
from app.models.users import User


router = APIRouter(tags=["member"])


@router.post("/member/installments/{installment_id}/mark-paid")
def mark_paid(
    installment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    mark_installment_paid(db=db, installment_id=installment_id)
    return {"message": "Installment marked as paid."}
