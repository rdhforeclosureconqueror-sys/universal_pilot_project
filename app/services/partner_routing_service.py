from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.housing_intelligence import PartnerOrganization, PartnerReferral


CATEGORY_TO_SERVICE_TYPE = {
    "legal_defense": "legal_defense",
    "loan_modification": "loan_modification",
    "nonprofit_support": "nonprofit_support",
    "property_acquisition": "property_acquisition",
}


def route_case_to_partner(
    db: Session,
    *,
    case_id: UUID,
    state: str,
    routing_category: str,
    actor_id: UUID | None,
) -> PartnerReferral:
    service_type = CATEGORY_TO_SERVICE_TYPE.get(routing_category)
    if not service_type:
        raise HTTPException(status_code=400, detail="Unsupported routing category")

    partner = (
        db.query(PartnerOrganization)
        .filter(PartnerOrganization.service_type == service_type)
        .filter((PartnerOrganization.service_region.is_(None)) | (PartnerOrganization.service_region == state))
        .first()
    )
    if not partner:
        raise HTTPException(status_code=404, detail="No partner organization available for routing")

    referral = PartnerReferral(
        case_id=case_id,
        partner_organization_id=partner.id,
        routing_category=routing_category,
        status="queued",
    )
    db.add(referral)
    db.flush()

    db.add(
        AuditLog(
            id=uuid4(),
            case_id=case_id,
            actor_id=actor_id,
            actor_is_ai=False,
            action_type="partner_case_routed",
            reason_code=f"partner_routed_{routing_category}",
            before_state={},
            after_state={"partner_organization_id": str(partner.id), "routing_category": routing_category},
            policy_version_id=None,
        )
    )

    return referral
