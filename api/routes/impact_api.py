from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import require_role
from app.models.users import UserRole
from db.session import get_db
from app.services.impact_analytics_service import get_impact_summary, get_opportunity_map
from app.services.platform_capability_service import get_platform_capabilities


router = APIRouter(tags=["Impact API"])


@router.get("/impact/summary")
def impact_summary(
    db: Session = Depends(get_db),
    _user=Depends(require_role([UserRole.admin, UserRole.audit_steward, UserRole.partner_org])),
):
    return get_impact_summary(db)


@router.get("/impact/opportunity-map")
def impact_opportunity_map(
    db: Session = Depends(get_db),
    _user=Depends(require_role([UserRole.admin, UserRole.audit_steward, UserRole.partner_org])),
):
    return {"states": get_opportunity_map(db)}


@router.get("/platform/capabilities")
def platform_capabilities(
    _user=Depends(require_role([UserRole.admin, UserRole.audit_steward, UserRole.partner_org])),
):
    return {"capabilities": get_platform_capabilities()}
