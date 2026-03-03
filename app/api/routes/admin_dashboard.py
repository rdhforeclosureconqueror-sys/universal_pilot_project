from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.admin_dashboard import AdminMembershipDetailResponse, AdminMembershipListResponse
from app.services.admin_dashboard_service import (
    get_membership_detail,
    list_memberships,
    memberships_below_stability,
    memberships_with_missed_installments,
)
from auth.dependencies import require_role
from db.session import get_db
from app.models.users import User, UserRole


router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


@router.get(
    "/memberships",
    response_model=AdminMembershipListResponse,
    dependencies=[Depends(require_role([UserRole.admin, UserRole.audit_steward]))],
)
def get_memberships(
    program_key: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return list_memberships(db, program_key=program_key, status=status, limit=limit, offset=offset)


@router.get(
    "/memberships/below-stability",
    response_model=AdminMembershipListResponse,
    dependencies=[Depends(require_role([UserRole.admin, UserRole.audit_steward]))],
)
def get_below_stability(
    threshold: int = 65,
    program_key: str | None = None,
    status: str = "active",
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return memberships_below_stability(
        db,
        threshold=threshold,
        program_key=program_key,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/memberships/missed-installments",
    response_model=AdminMembershipListResponse,
    dependencies=[Depends(require_role([UserRole.admin, UserRole.audit_steward]))],
)
def get_missed_installments(
    program_key: str | None = None,
    status: str = "active",
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return memberships_with_missed_installments(
        db,
        program_key=program_key,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/memberships/{membership_id}",
    response_model=AdminMembershipDetailResponse,
    dependencies=[Depends(require_role([UserRole.admin, UserRole.audit_steward]))],
)
def get_membership(
    membership_id: UUID,
    db: Session = Depends(get_db),
):
    return get_membership_detail(db, membership_id)
