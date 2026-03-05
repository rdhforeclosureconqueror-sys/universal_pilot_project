from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog
from app.models.documents import Document
from app.models.enums import DocumentType
from app.models.veteran_intelligence import BenefitDiscoveryAggregate, BenefitProgress, BenefitRegistry, VeteranProfile
from app.services.workflow_service import advance_to_risk_stage


CATEGORY_STANDARD_VETERAN = "STANDARD_VETERAN"
CATEGORY_DISABLED_VETERAN = "DISABLED_VETERAN"
CATEGORY_50_PERCENT_DISABLED = "50_PERCENT_DISABLED"
CATEGORY_70_PERCENT_DISABLED = "70_PERCENT_DISABLED"
CATEGORY_100_PERCENT_DISABLED = "100_PERCENT_DISABLED"
CATEGORY_100_PERCENT_PERMANENT_TOTAL = "100_PERCENT_PERMANENT_TOTAL"
CATEGORY_COMBAT_VETERAN = "COMBAT_VETERAN"
CATEGORY_MEDICALLY_RETIRED = "MEDICALLY_RETIRED"


DEFAULT_BENEFITS = [
    {
        "benefit_name": "VA_HOME_LOAN",
        "eligibility_rules": {"requires_discharge": ["honorable", "general"], "min_years_of_service": 2},
        "required_documents": ["DD214", "VA Form 26-1880", "income_verification"],
        "estimated_value": 15000.0,
        "application_steps": ["Request VA Certificate of Eligibility", "Apply through approved VA lender"],
    },
    {
        "benefit_name": "VA_IRRRL_REFINANCE",
        "eligibility_rules": {"requires_homeowner": True, "requires_mortgage_status": ["active_va_loan"]},
        "required_documents": ["current_mortgage_statement", "hardship_letter"],
        "estimated_value": 8500.0,
        "application_steps": ["Apply for VA IRRRL refinance", "Submit updated income package"],
    },
    {
        "benefit_name": "VA_FORECLOSURE_ASSISTANCE",
        "eligibility_rules": {"requires_foreclosure_risk": True},
        "required_documents": ["hardship_letter", "mortgage_statement", "budget"],
        "estimated_value": 12000.0,
        "application_steps": ["Open VA loan technician case", "Submit hardship package"],
    },
    {
        "benefit_name": "SPECIAL_ADAPTED_HOUSING_GRANT",
        "eligibility_rules": {"min_disability_rating": 70},
        "required_documents": ["medical_rating_letter", "grant_application"],
        "estimated_value": 109986.0,
        "application_steps": ["Submit SAH application", "Schedule housing suitability review"],
    },
    {
        "benefit_name": "SPECIAL_HOUSING_ADAPTATION_GRANT",
        "eligibility_rules": {"min_disability_rating": 50},
        "required_documents": ["medical_rating_letter", "home_mod_scope"],
        "estimated_value": 22036.0,
        "application_steps": ["Submit SHA application", "Submit contractor estimates"],
    },
    {
        "benefit_name": "DISABLED_VETERAN_PROPERTY_TAX_EXEMPTION",
        "eligibility_rules": {"min_disability_rating": 50},
        "required_documents": ["state_tax_form", "disability_rating_letter"],
        "estimated_value": 4500.0,
        "application_steps": ["Apply with county assessor", "Provide VA disability documentation"],
    },
    {
        "benefit_name": "HUD_VASH_HOUSING_ASSISTANCE",
        "eligibility_rules": {"requires_income_level_any_of": ["low", "very_low"], "requires_foreclosure_risk": True},
        "required_documents": ["income_docs", "housing_instability_statement"],
        "estimated_value": 18000.0,
        "application_steps": ["Complete HUD-VASH intake", "Coordinate with VA case manager"],
    },
]


def upsert_veteran_profile(db: Session, *, actor_id: UUID | None, payload: dict) -> VeteranProfile:
    case_id = _uuid(payload.get("case_id"), field="case_id")
    profile = db.query(VeteranProfile).filter(VeteranProfile.case_id == case_id).first()
    if not profile:
        profile = VeteranProfile(case_id=case_id)
        db.add(profile)

    for field in [
        "branch_of_service",
        "years_of_service",
        "discharge_status",
        "disability_rating",
        "permanent_and_total_status",
        "combat_service",
        "dependent_status",
        "state_of_residence",
        "homeowner_status",
        "mortgage_status",
        "foreclosure_risk",
        "income_level",
    ]:
        if field in payload:
            setattr(profile, field, payload[field])

    db.flush()
    _audit(db, actor_id=actor_id, case_id=case_id, action_type="veteran_profile_upserted", reason_code="profile_updated", after_state={"case_id": str(case_id)})
    return profile


def categorize_profile(profile: VeteranProfile) -> list[str]:
    categories = [CATEGORY_STANDARD_VETERAN]

    rating = profile.disability_rating or 0
    if rating > 0:
        categories.append(CATEGORY_DISABLED_VETERAN)
    if rating >= 50:
        categories.append(CATEGORY_50_PERCENT_DISABLED)
    if rating >= 70:
        categories.append(CATEGORY_70_PERCENT_DISABLED)
    if rating >= 100:
        categories.append(CATEGORY_100_PERCENT_DISABLED)
    if rating >= 100 and profile.permanent_and_total_status:
        categories.append(CATEGORY_100_PERCENT_PERMANENT_TOTAL)

    if profile.combat_service:
        categories.append(CATEGORY_COMBAT_VETERAN)

    discharge = (profile.discharge_status or "").lower()
    if "medical" in discharge or "retire" in discharge:
        categories.append(CATEGORY_MEDICALLY_RETIRED)

    return sorted(set(categories))


def ensure_benefit_registry_seeded(db: Session) -> None:
    existing_names = {row.benefit_name for row in db.query(BenefitRegistry).all()}
    for benefit in DEFAULT_BENEFITS:
        if benefit["benefit_name"] in existing_names:
            continue
        db.add(BenefitRegistry(**benefit))
    db.flush()


def match_benefits(db: Session, *, case_id: UUID) -> dict:
    profile = db.query(VeteranProfile).filter(VeteranProfile.case_id == case_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Veteran profile not found")

    ensure_benefit_registry_seeded(db)
    benefits = db.query(BenefitRegistry).filter(BenefitRegistry.is_active.is_(True)).all()

    matched: list[BenefitRegistry] = []
    for benefit in benefits:
        if _benefit_matches(profile, benefit):
            matched.append(benefit)

    priority_order = [b.benefit_name for b in sorted(matched, key=lambda b: (b.estimated_value or 0), reverse=True)]
    estimated_total_value = sum((b.estimated_value or 0) for b in matched)

    for benefit_name in priority_order:
        _upsert_progress(db, case_id=case_id, benefit_name=benefit_name, status="IN_PROGRESS", status_notes="Auto-identified")

    _update_aggregate(db, profile=profile, benefit_names=priority_order)

    if profile.foreclosure_risk:
        advance_to_risk_stage(db, case_id)

    return {
        "eligible_benefits": priority_order,
        "estimated_total_value": estimated_total_value,
        "priority_order": priority_order,
        "categories": categorize_profile(profile),
    }


def generate_action_plan(db: Session, *, case_id: UUID) -> dict:
    matches = match_benefits(db, case_id=case_id)
    steps: list[str] = ["Request VA Certificate of Eligibility"]

    if "VA_IRRRL_REFINANCE" in matches["eligible_benefits"]:
        steps.append("Apply for VA IRRRL refinance")
    if "DISABLED_VETERAN_PROPERTY_TAX_EXEMPTION" in matches["eligible_benefits"]:
        steps.append("Apply for state property tax exemption")
    if "SPECIAL_ADAPTED_HOUSING_GRANT" in matches["eligible_benefits"]:
        steps.append("Submit SAH housing grant application")

    for idx, benefit in enumerate(matches["eligible_benefits"], start=1):
        if idx > 4:
            steps.append(f"Apply for {benefit}")

    return {"steps": steps, "match_summary": matches}


def generate_documents(db: Session, *, case_id: UUID, actor_id: UUID) -> dict:
    profile = db.query(VeteranProfile).filter(VeteranProfile.case_id == case_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Veteran profile not found")

    forms = [
        "VA Form 26-1880",
        "VA hardship letter",
        "loan modification package",
        "grant application package",
    ]
    created_ids: list[str] = []
    for form_name in forms:
        doc = Document(
            case_id=case_id,
            uploaded_by=actor_id,
            doc_type=DocumentType.other,
            meta={
                "generated_by": "veteran_intelligence_platform",
                "form_name": form_name,
                "auto_populated": True,
                "profile_snapshot": {
                    "branch_of_service": profile.branch_of_service,
                    "disability_rating": profile.disability_rating,
                    "state_of_residence": profile.state_of_residence,
                },
            },
            file_url=f"generated://veteran/{case_id}/{form_name.replace(' ', '_')}.json",
        )
        db.add(doc)
        db.flush()
        created_ids.append(str(doc.id))

    _audit(
        db,
        actor_id=actor_id,
        case_id=case_id,
        action_type="veteran_documents_generated",
        reason_code="documents_auto_generated",
        after_state={"document_ids": created_ids},
    )

    return {"generated_documents": created_ids, "forms": forms}


def update_benefit_progress(db: Session, *, case_id: UUID, benefit_name: str, status: str, status_notes: str | None, actor_id: UUID | None) -> dict:
    allowed = {"NOT_STARTED", "IN_PROGRESS", "SUBMITTED", "APPROVED", "REJECTED"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status '{status}'")

    progress = _upsert_progress(db, case_id=case_id, benefit_name=benefit_name, status=status, status_notes=status_notes, updated_by=actor_id)
    return {
        "case_id": str(progress.case_id),
        "benefit_name": progress.benefit_name,
        "status": progress.status,
        "status_notes": progress.status_notes,
    }


def get_advisory(db: Session, *, case_id: UUID, question: str) -> dict:
    profile = db.query(VeteranProfile).filter(VeteranProfile.case_id == case_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Veteran profile not found")

    matches = match_benefits(db, case_id=case_id)
    q = question.lower()
    if "refinance" in q:
        answer = "You may qualify for VA IRRRL refinance if your mortgage status is active_va_loan and your profile is current."
    elif "foreclosure" in q:
        answer = "Foreclosure mitigation is available. We recommend hardship package submission and legal assistance referral immediately."
    else:
        answer = f"You currently match {len(matches['eligible_benefits'])} benefits: {', '.join(matches['eligible_benefits'])}."

    return {
        "question": question,
        "answer": answer,
        "categories": categorize_profile(profile),
        "eligible_benefits": matches["eligible_benefits"],
        "estimated_total_value": matches["estimated_total_value"],
    }


def partner_aggregate_report(db: Session, *, state_of_residence: str | None = None) -> list[dict]:
    query = db.query(BenefitDiscoveryAggregate)
    if state_of_residence:
        query = query.filter(BenefitDiscoveryAggregate.state_of_residence == state_of_residence)
    rows = query.order_by(BenefitDiscoveryAggregate.discovery_count.desc()).all()
    return [
        {
            "state_of_residence": r.state_of_residence,
            "benefit_name": r.benefit_name,
            "discovery_count": r.discovery_count,
            "last_discovered_at": r.last_discovered_at,
        }
        for r in rows
    ]


def _benefit_matches(profile: VeteranProfile, benefit: BenefitRegistry) -> bool:
    rules = benefit.eligibility_rules or {}
    if rules.get("requires_discharge"):
        if (profile.discharge_status or "").lower() not in rules["requires_discharge"]:
            return False

    min_years = rules.get("min_years_of_service")
    if min_years is not None and (profile.years_of_service or 0) < int(min_years):
        return False

    min_rating = rules.get("min_disability_rating")
    if min_rating is not None and (profile.disability_rating or 0) < int(min_rating):
        return False

    if rules.get("requires_homeowner") and not profile.homeowner_status:
        return False

    if rules.get("requires_mortgage_status"):
        if (profile.mortgage_status or "").lower() not in [x.lower() for x in rules["requires_mortgage_status"]]:
            return False

    if rules.get("requires_foreclosure_risk") and not profile.foreclosure_risk:
        return False

    income_levels = rules.get("requires_income_level_any_of")
    if income_levels and (profile.income_level or "").lower() not in [x.lower() for x in income_levels]:
        return False

    return True


def _upsert_progress(
    db: Session,
    *,
    case_id: UUID,
    benefit_name: str,
    status: str,
    status_notes: str | None,
    updated_by: UUID | None = None,
) -> BenefitProgress:
    progress = (
        db.query(BenefitProgress)
        .filter(BenefitProgress.case_id == case_id, BenefitProgress.benefit_name == benefit_name)
        .first()
    )
    if not progress:
        progress = BenefitProgress(case_id=case_id, benefit_name=benefit_name)
        db.add(progress)

    progress.status = status
    progress.status_notes = status_notes
    progress.updated_by = updated_by
    db.flush()
    return progress


def _update_aggregate(db: Session, *, profile: VeteranProfile, benefit_names: list[str]) -> None:
    state = profile.state_of_residence or "UNKNOWN"
    for benefit_name in benefit_names:
        row = (
            db.query(BenefitDiscoveryAggregate)
            .filter(
                BenefitDiscoveryAggregate.state_of_residence == state,
                BenefitDiscoveryAggregate.benefit_name == benefit_name,
            )
            .first()
        )
        if not row:
            row = BenefitDiscoveryAggregate(state_of_residence=state, benefit_name=benefit_name, discovery_count=0)
            db.add(row)
        row.discovery_count = int(row.discovery_count or 0) + 1
        row.last_discovered_at = datetime.now(timezone.utc)


def _audit(
    db: Session,
    *,
    actor_id: UUID | None,
    case_id: UUID,
    action_type: str,
    reason_code: str,
    after_state: dict,
) -> None:
    db.add(
        AuditLog(
            id=uuid4(),
            case_id=case_id,
            actor_id=actor_id,
            actor_is_ai=False,
            action_type=action_type,
            reason_code=reason_code,
            before_state={},
            after_state=after_state,
            policy_version_id=None,
        )
    )


def _uuid(value: str | None, *, field: str) -> UUID:
    if not value:
        raise HTTPException(status_code=400, detail=f"{field} is required")
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field} must be a valid UUID") from exc

