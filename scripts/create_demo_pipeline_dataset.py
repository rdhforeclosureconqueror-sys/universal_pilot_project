"""Create a complete demo housing intervention pipeline dataset.

Creates/updates:
1) User (Michael Ramirez)
2) Property (101 Elm St)
3) Lead (referencing property via raw_payload)
4) Case (referencing lead via meta + created_by user)
5) Foreclosure profile (linked to case)
6) Essential worker profile (Sarah Johnson)

Prints created IDs as JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.session import SessionLocal
from auth.auth_handler import hash_password
from app.models.users import User, UserRole
from app.models.properties import Property
from app.models.lead_intelligence import LeadSource, PropertyLead
from app.models.cases import Case
from app.models.enums import CaseStatus
from app.models.housing_intelligence import ForeclosureCaseData
from app.models.essential_worker import EssentialWorkerProfile


USER_ID = UUID("11111111-1111-4111-8111-111111111111")
PROPERTY_ID = UUID("22222222-2222-4222-8222-222222222222")
LEAD_SOURCE_ID = UUID("33333333-3333-4333-8333-333333333333")
LEAD_ID = UUID("44444444-4444-4444-8444-444444444444")
CASE_ID = UUID("55555555-5555-4555-8555-555555555555")
FORECLOSURE_ID = UUID("66666666-6666-4666-8666-666666666666")
WORKER_PROFILE_ID = UUID("77777777-7777-4777-8777-777777777777")


def upsert_user(db):
    user = db.query(User).filter(User.id == USER_ID).first()
    if not user:
        user = User(id=USER_ID)
    user.email = "michael.ramirez@demo.universalpilot.local"
    user.full_name = "Michael Ramirez"
    user.role = UserRole.case_worker
    user.hashed_password = hash_password("DemoPassword123!")
    db.add(user)
    return user


def upsert_property(db):
    prop = db.query(Property).filter(Property.id == PROPERTY_ID).first()
    if not prop:
        prop = Property(id=PROPERTY_ID)
    prop.external_id = "DEMO-101-ELM-ST"
    prop.address = "101 Elm St"
    prop.city = "Dallas"
    prop.state = "TX"
    prop.zip = "75201"
    prop.assessed_value = 320000
    prop.est_balance = 240000
    prop.loan_type = "conventional"
    prop.source = "demo_pipeline"
    prop.latitude = 32.7767
    prop.longitude = -96.7970
    db.add(prop)
    return prop


def upsert_lead_source(db):
    source = db.query(LeadSource).filter(LeadSource.id == LEAD_SOURCE_ID).first()
    if not source:
        source = LeadSource(id=LEAD_SOURCE_ID)
    source.source_name = "demo_pipeline_source"
    source.source_type = "seed"
    db.add(source)
    return source


def upsert_property_lead(db):
    lead = db.query(PropertyLead).filter(PropertyLead.id == LEAD_ID).first()
    if not lead:
        lead = PropertyLead(id=LEAD_ID)
    lead.source_id = LEAD_SOURCE_ID
    lead.property_address = "101 Elm St"
    lead.city = "Dallas"
    lead.state = "TX"
    lead.zip_code = "75201"
    lead.foreclosure_stage = "pre_foreclosure"
    lead.equity_estimate = 80000.0
    lead.tax_delinquent = "unknown"
    lead.owner_occupancy = "owner_occupied"
    lead.raw_payload = {
        "property_id": str(PROPERTY_ID),
        "estimated_value": 320000,
        "loan_balance": 240000,
        "arrears_amount": 12000,
    }
    db.add(lead)
    return lead


def upsert_case(db):
    case = db.query(Case).filter(Case.id == CASE_ID).first()
    if not case:
        case = Case(id=CASE_ID)
    case.status = CaseStatus.in_progress
    case.created_by = USER_ID
    case.program_type = "foreclosure_intervention"
    case.program_key = "DFW_HOUSING_RESCUE"
    case.property_id = PROPERTY_ID
    case.case_type = "housing_intervention"
    case.canonical_key = "demo-case-101-elm"
    case.meta = {
        "lead_id": str(LEAD_ID),
        "lead_property_id": str(PROPERTY_ID),
        "source": "demo_pipeline",
        "owner_name": "Michael Ramirez",
    }
    db.add(case)
    return case


def upsert_foreclosure_profile(db):
    fc = db.query(ForeclosureCaseData).filter(ForeclosureCaseData.id == FORECLOSURE_ID).first()
    if not fc:
        fc = ForeclosureCaseData(id=FORECLOSURE_ID)
    fc.case_id = CASE_ID
    fc.property_address = "101 Elm St"
    fc.city = "Dallas"
    fc.state = "TX"
    fc.zip_code = "75201"
    fc.loan_balance = 240000.0
    fc.estimated_property_value = 320000.0
    fc.arrears_amount = 12000.0
    fc.foreclosure_stage = "pre_foreclosure"
    fc.homeowner_income = 68000.0
    fc.homeowner_hardship_reason = "medical_expense_spike"
    fc.occupancy_status = "owner_occupied"
    db.add(fc)
    return fc


def upsert_worker_profile(db):
    profile = db.query(EssentialWorkerProfile).filter(EssentialWorkerProfile.id == WORKER_PROFILE_ID).first()
    if not profile:
        profile = EssentialWorkerProfile(id=WORKER_PROFILE_ID)
    profile.case_id = CASE_ID
    profile.user_id = USER_ID
    profile.profession = "nurse"
    profile.employer_type = "hospital"
    profile.annual_income = 68000.0
    profile.city = "Dallas"
    profile.state = "TX"
    profile.first_time_homebuyer = "true"
    db.add(profile)
    return profile


def main() -> None:
    db = SessionLocal()
    try:
        upsert_user(db)
        upsert_property(db)
        upsert_lead_source(db)
        upsert_property_lead(db)
        upsert_case(db)
        upsert_foreclosure_profile(db)
        upsert_worker_profile(db)
        db.commit()

        output = {
            "user_id": str(USER_ID),
            "property_id": str(PROPERTY_ID),
            "lead_source_id": str(LEAD_SOURCE_ID),
            "lead_id": str(LEAD_ID),
            "case_id": str(CASE_ID),
            "foreclosure_case_data_id": str(FORECLOSURE_ID),
            "essential_worker_profile_id": str(WORKER_PROFILE_ID),
        }
        print(json.dumps(output, indent=2))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
