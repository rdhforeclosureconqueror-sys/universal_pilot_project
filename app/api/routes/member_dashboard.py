from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.member_dashboard import MemberDashboardResponse
from app.services.member_dashboard_service import get_member_dashboard
from auth.dependencies import get_current_user
from db.session import get_db
from models.users import User


router = APIRouter(tags=["member"])


@router.get("/member/dashboard", response_model=MemberDashboardResponse)
def read_member_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_member_dashboard(db, current_user.id)
