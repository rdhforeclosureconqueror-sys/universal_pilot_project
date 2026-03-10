from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from db.session import get_db
from app.services.partner_routing_service import route_case_to_partner


router = APIRouter(prefix="/partners", tags=["Housing Partner Routing"])


class RouteCaseRequest(BaseModel):
    case_id: UUID
    state: str
    routing_category: str


@router.post("/route-case")
def route_case(
    request: RouteCaseRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="partners.route_case")

    referral = route_case_to_partner(
        db,
        case_id=request.case_id,
        state=request.state,
        routing_category=request.routing_category,
        actor_id=user.id,
    )
    db.commit()

    return {
        "partner_referral_id": str(referral.id),
        "case_id": str(referral.case_id),
        "routing_category": referral.routing_category,
        "status": referral.status,
    }
