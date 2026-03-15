from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from db.session import get_db
from app.services.essential_worker_housing_service import (
    discover_housing_programs,
    generate_homebuyer_action_plan,
    generate_required_documents,
    upsert_worker_profile,
)


router = APIRouter(prefix="/essential-worker", tags=["Essential Worker Housing"])


class EssentialWorkerProfileRequest(BaseModel):
    case_id: UUID | None = None
    user_id: UUID | None = None
    profession: str
    employer_type: str | None = None
    state: str
    city: str | None = None
    annual_income: float | None = None
    first_time_homebuyer: str | None = None


class EssentialWorkerDiscoverRequest(BaseModel):
    case_id: UUID
    profile_id: UUID


@router.post("/profile")
def create_or_update_profile(
    request: EssentialWorkerProfileRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if request.case_id:
        PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="essential_worker.profile")
    profile = upsert_worker_profile(db, payload=request.model_dump(exclude_none=True), actor_id=user.id)
    db.commit()
    return {"profile_id": str(profile.id), "profession": profile.profession, "state": profile.state}


@router.post("/discover-benefits")
def discover_benefits(
    request: EssentialWorkerDiscoverRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="essential_worker.discover")
    result = discover_housing_programs(db, profile_id=request.profile_id)
    db.commit()
    return result


@router.post("/action-plan")
def action_plan(
    request: EssentialWorkerDiscoverRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="essential_worker.action_plan")
    plan = generate_homebuyer_action_plan(db, profile_id=request.profile_id)
    docs = generate_required_documents(db, profile_id=request.profile_id)
    return {"action_plan": plan["steps"], "required_documents": docs["documents"]}
