from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.foreclosure_intelligence import ForeclosureAnalyzeRequest, ForeclosureCreateRequest
from app.schemas.application import ApplicationCreate
from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from db.session import get_db
from app.models.audit_logs import AuditLog
from app.models.cases import Case
from app.models.housing_intelligence import ForeclosureCaseData
from app.services.action_payload_builder import ActionExecutionContext, build_action_payload
from app.services.application_service import submit_application
from app.services.foreclosure_intelligence_service import (
    calculate_case_priority,
    create_foreclosure_profile,
    update_foreclosure_status,
)
from app.services.property_analysis_service import (
    calculate_acquisition_score,
    calculate_equity,
    calculate_ltv,
    calculate_rescue_score,
    classify_intervention,
)
from app.services.partner_routing_service import route_case_to_partner


router = APIRouter(prefix="/foreclosure", tags=["Foreclosure Intelligence"])


@router.post("/create-profile")
def create_profile(
    request: ForeclosureCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if request.case_id:
        PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="foreclosure.profile.create")

    payload = request.model_dump(exclude={"case_id"}, exclude_none=True)
    result = create_foreclosure_profile(db, case_id=request.case_id, payload=payload, actor_id=user.id)
    db.commit()

    return {
        "case_id": str(result["case_id"]),
        "profile_created": bool(result["profile_created"]),
    }


@router.post("/analyze-property")
def analyze_property(
    request: ForeclosureAnalyzeRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not request.case_id:
        raise HTTPException(status_code=422, detail="case_id is required")
    PolicyAuthorizer(db).require_case_action(user=user, case_id=str(request.case_id), action="foreclosure.property.analyze")

    equity = calculate_equity(estimated_property_value=request.estimated_property_value, loan_balance=request.loan_balance)
    ltv = calculate_ltv(loan_balance=request.loan_balance, estimated_property_value=request.estimated_property_value)
    rescue_score = calculate_rescue_score(
        arrears_amount=request.arrears_amount,
        homeowner_income=request.homeowner_income or 0,
        foreclosure_stage=request.foreclosure_stage,
    )
    acquisition_score = calculate_acquisition_score(equity=equity, ltv=ltv, foreclosure_stage=request.foreclosure_stage)
    classification = classify_intervention(rescue_score=rescue_score, acquisition_score=acquisition_score, ltv=ltv)
    priority = calculate_case_priority(db, case_id=request.case_id)

    return {
        "case_id": str(request.case_id),
        "equity": equity,
        "ltv": ltv,
        "rescue_score": rescue_score,
        "acquisition_score": acquisition_score,
        "classification": classification,
        "priority": priority,
    }


@router.post("/intake/public")
def submit_public_foreclosure_intake(
    request: ForeclosureCreateRequest,
    db: Session = Depends(get_db),
):
    contact_email = (request.contact_email or "").strip()
    if not contact_email:
        raise HTTPException(status_code=422, detail="contact_email is required")

    submit_application(
        db,
        ApplicationCreate(
            email=contact_email,
            full_name=request.full_name,
            phone=request.phone,
            program_key=request.program_key or "foreclosure_assistance",
            answers_json={
                "consent_acknowledged": request.consent_acknowledged,
                "timeline_notes": request.timeline_notes,
                "lead_id": str(request.lead_id) if request.lead_id else None,
            },
        ),
    )

    payload = request.model_dump(
        exclude={
            "case_id",
            "full_name",
            "contact_email",
            "phone",
            "consent_acknowledged",
            "timeline_notes",
            "lead_id",
            "program_key",
        },
        exclude_none=True,
    )

    result = create_foreclosure_profile(
        db,
        case_id=None,
        payload=payload,
        actor_id=None,
        case_meta={
            "intake_source": "public_help_foreclosure",
            "full_name": request.full_name,
            "contact_email": contact_email,
            "phone": request.phone,
            "consent_acknowledged": request.consent_acknowledged,
            "timeline_notes": request.timeline_notes,
            "lead_id": str(request.lead_id) if request.lead_id else None,
        },
    )
    db.commit()

    return {
        "status": "submitted",
        "case_id": str(result["case_id"]),
        "message": "Foreclosure intake submitted. A housing specialist will review your case within 1 business day.",
    }


@router.get("/workspace/cases")
def get_foreclosure_workspace_cases(
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

    return [
        {
            "case_id": str(case.id),
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "property_address": profile.property_address,
            "city": profile.city,
            "state": profile.state,
            "foreclosure_stage": profile.foreclosure_stage,
            "arrears_amount": profile.arrears_amount,
            "homeowner_income": profile.homeowner_income,
            "contact_email": (case.meta or {}).get("contact_email"),
            "lead_id": (case.meta or {}).get("lead_id"),
        }
        for case, profile in rows
    ]


@router.get("/workspace/cases/{case_id}")
def get_foreclosure_workspace_case_detail(
    case_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    case = db.query(Case).filter(Case.id == case_id).first()
    profile = db.query(ForeclosureCaseData).filter(ForeclosureCaseData.case_id == case_id).first()
    if not case or not profile:
        raise HTTPException(status_code=404, detail="Foreclosure case not found")

    audits = (
        db.query(AuditLog)
        .filter(AuditLog.case_id == case_id)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )
    priority = calculate_case_priority(db, case_id=case_id)

    return {
        "case_id": str(case.id),
        "status": case.status.value if case.status else None,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "meta": case.meta or {},
        "profile": {
            "property_address": profile.property_address,
            "city": profile.city,
            "state": profile.state,
            "zip_code": profile.zip_code,
            "loan_balance": profile.loan_balance,
            "estimated_property_value": profile.estimated_property_value,
            "arrears_amount": profile.arrears_amount,
            "foreclosure_stage": profile.foreclosure_stage,
            "lender_name": profile.lender_name,
            "servicer_name": profile.servicer_name,
            "homeowner_income": profile.homeowner_income,
            "homeowner_hardship_reason": profile.homeowner_hardship_reason,
        },
        "priority": priority,
        "audit_log": [
            {
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "action_type": row.action_type,
                "reason_code": row.reason_code,
            }
            for row in audits
        ],
    }


@router.post("/workspace/cases/{case_id}/actions/analyze")
def workspace_analyze_case(
    case_id: UUID,
    request: ForeclosureAnalyzeRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    payload = build_action_payload(
        "analyze_property",
        request.model_dump(exclude_none=True),
        context=ActionExecutionContext(case_id=case_id, actor_id=user.id),
    )
    equity = calculate_equity(estimated_property_value=payload["estimated_property_value"], loan_balance=payload["loan_balance"])
    ltv = calculate_ltv(loan_balance=payload["loan_balance"], estimated_property_value=payload["estimated_property_value"])
    rescue_score = calculate_rescue_score(
        arrears_amount=payload["arrears_amount"],
        homeowner_income=payload.get("homeowner_income") or 0,
        foreclosure_stage=payload["foreclosure_stage"],
    )
    acquisition_score = calculate_acquisition_score(equity=equity, ltv=ltv, foreclosure_stage=payload["foreclosure_stage"])
    classification = classify_intervention(rescue_score=rescue_score, acquisition_score=acquisition_score, ltv=ltv)
    return {
        "case_id": str(case_id),
        "equity": equity,
        "ltv": ltv,
        "rescue_score": rescue_score,
        "acquisition_score": acquisition_score,
        "classification": classification,
    }


@router.post("/workspace/cases/{case_id}/actions/next-step")
def workspace_trigger_next_step(
    case_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    case = db.query(Case).filter(Case.id == case_id).first()
    profile = db.query(ForeclosureCaseData).filter(ForeclosureCaseData.case_id == case_id).first()
    if not case or not profile:
        raise HTTPException(status_code=404, detail="Foreclosure case not found")

    stage_order = ["pre_foreclosure", "notice_of_default", "auction_scheduled", "post_sale"]
    current_stage = (profile.foreclosure_stage or "pre_foreclosure").lower()
    try:
        idx = stage_order.index(current_stage)
    except ValueError:
        idx = 0
    next_stage = stage_order[min(idx + 1, len(stage_order) - 1)]
    update_foreclosure_status(db, case_id=case_id, foreclosure_stage=next_stage, actor_id=user.id)

    route = route_case_to_partner(
        db,
        case_id=case_id,
        state=profile.state or "TX",
        routing_category="nonprofit_support",
        actor_id=user.id,
    )
    db.commit()
    return {
        "case_id": str(case_id),
        "next_stage": next_stage,
        "partner_referral_id": str(route.id),
        "partner_referral_status": route.status,
    }
