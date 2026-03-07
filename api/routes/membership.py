from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from db.session import get_db
from app.services.membership_service import create_membership


router = APIRouter(prefix="/membership", tags=["Membership"])


class MembershipCreateRequest(BaseModel):
    case_id: UUID
    user_id: UUID
    membership_type: str = "cooperative"


@router.post("/create")
def create_membership_profile(
    request: MembershipCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="membership.create")

    profile = create_membership(
        db,
        user_id=request.user_id,
        case_id=request.case_id,
        membership_type=request.membership_type,
        actor_id=user.id,
    )
    db.commit()

    return {
        "membership_profile_id": str(profile.id),
        "membership_status": profile.membership_status,
        "membership_type": profile.membership_type,
    }
