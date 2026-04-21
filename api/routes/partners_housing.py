from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from db.session import get_db
from app.models.audit_logs import AuditLog
from app.models.cases import Case
from app.models.housing_intelligence import ForeclosureCaseData, PartnerOrganization, PartnerReferral
from app.services.partner_routing_service import route_case_to_partner


router = APIRouter(prefix="/partners", tags=["Housing Partner Routing"])


class RouteCaseRequest(BaseModel):
    case_id: UUID
    state: str
    routing_category: str


class WorkspaceRouteCaseRequest(BaseModel):
    partner_organization_id: UUID | None = None
    state: str
    routing_category: str
    routing_reason: str | None = None


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


@router.get("/workspace/cases")
def get_partner_routing_workspace_cases(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    rows = (
        db.query(Case, ForeclosureCaseData)
        .join(ForeclosureCaseData, ForeclosureCaseData.case_id == Case.id)
        .order_by(Case.created_at.desc())
        .limit(200)
        .all()
    )

    case_ids = [case.id for case, _profile in rows]
    routed_case_ids = {
        row[0]
        for row in db.query(PartnerReferral.case_id)
        .filter(PartnerReferral.case_id.in_(case_ids))
        .all()
    }

    items = []
    for case, profile in rows:
        if case.id in routed_case_ids:
            continue
        items.append(
            {
                "case_id": str(case.id),
                "property_address": profile.property_address,
                "city": profile.city,
                "state": profile.state,
                "foreclosure_stage": profile.foreclosure_stage,
                "status": case.status.value if case.status else None,
                "created_at": case.created_at.isoformat() if case.created_at else None,
            }
        )
    return items


@router.get("/workspace/cases/{case_id}")
def get_partner_routing_workspace_case_detail(
    case_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    case = db.query(Case).filter(Case.id == case_id).first()
    profile = db.query(ForeclosureCaseData).filter(ForeclosureCaseData.case_id == case_id).first()
    if not case or not profile:
        raise HTTPException(status_code=404, detail="Routing case not found")

    partners = (
        db.query(PartnerOrganization)
        .order_by(PartnerOrganization.name.asc())
        .limit(250)
        .all()
    )
    referrals = (
        db.query(PartnerReferral, PartnerOrganization)
        .join(PartnerOrganization, PartnerOrganization.id == PartnerReferral.partner_organization_id)
        .filter(PartnerReferral.case_id == case_id)
        .order_by(PartnerReferral.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "case": {
            "case_id": str(case.id),
            "status": case.status.value if case.status else None,
            "property_address": profile.property_address,
            "city": profile.city,
            "state": profile.state,
            "foreclosure_stage": profile.foreclosure_stage,
            "loan_balance": profile.loan_balance,
            "estimated_property_value": profile.estimated_property_value,
            "arrears_amount": profile.arrears_amount,
        },
        "partner_options": [
            {
                "partner_organization_id": str(partner.id),
                "name": partner.name,
                "service_type": partner.service_type,
                "service_region": partner.service_region,
            }
            for partner in partners
        ],
        "referral_history": [
            {
                "partner_referral_id": str(referral.id),
                "partner_name": partner.name,
                "routing_category": referral.routing_category,
                "status": referral.status,
                "notes": referral.notes,
                "created_at": referral.created_at.isoformat() if referral.created_at else None,
            }
            for referral, partner in referrals
        ],
    }


@router.post("/workspace/cases/{case_id}/actions/route")
def workspace_route_case(
    case_id: UUID,
    request: WorkspaceRouteCaseRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Routing case not found")

    PolicyAuthorizer(db).require_case_action(user=user, case_id=str(case_id), action="partners.route_case")

    if request.partner_organization_id:
        partner = db.query(PartnerOrganization).filter(PartnerOrganization.id == request.partner_organization_id).first()
        if not partner:
            raise HTTPException(status_code=404, detail="Selected partner not found")

        referral = PartnerReferral(
            case_id=case_id,
            partner_organization_id=partner.id,
            routing_category=request.routing_category,
            status="queued",
            notes=request.routing_reason,
        )
        db.add(referral)
        db.flush()
    else:
        referral = route_case_to_partner(
            db,
            case_id=case_id,
            state=request.state,
            routing_category=request.routing_category,
            actor_id=user.id,
        )
        referral.notes = request.routing_reason

    db.add(
        AuditLog(
            case_id=case_id,
            actor_id=user.id,
            actor_is_ai=False,
            action_type="partner_routing_submitted",
            reason_code=f"partner_routing_{request.routing_category}",
            before_state={},
            after_state={
                "partner_referral_id": str(referral.id),
                "routing_category": request.routing_category,
                "state": request.state,
                "routing_reason": request.routing_reason,
            },
            policy_version_id=None,
        )
    )

    db.commit()
    return {
        "partner_referral_id": str(referral.id),
        "case_id": str(referral.case_id),
        "routing_category": referral.routing_category,
        "status": referral.status,
        "routing_reason": referral.notes,
    }
