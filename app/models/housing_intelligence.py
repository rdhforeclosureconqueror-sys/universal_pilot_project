from datetime import datetime
import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base


class ForeclosureCaseData(Base):
    __tablename__ = "foreclosure_case_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, unique=True, index=True)

    property_address = Column(String, nullable=False)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    loan_balance = Column(Float, nullable=True)
    estimated_property_value = Column(Float, nullable=True)
    monthly_payment = Column(Float, nullable=True)
    arrears_amount = Column(Float, nullable=True)
    foreclosure_stage = Column(String, nullable=True)
    auction_date = Column(DateTime(timezone=True), nullable=True)
    lender_name = Column(String, nullable=True)
    servicer_name = Column(String, nullable=True)
    occupancy_status = Column(String, nullable=True)
    homeowner_income = Column(Float, nullable=True)
    homeowner_hardship_reason = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PartnerOrganization(Base):
    __tablename__ = "partner_organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    service_type = Column(String, nullable=False)
    service_region = Column(String, nullable=True)
    contact_info = Column(JSONB, nullable=True)
    api_endpoint = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class PartnerReferral(Base):
    __tablename__ = "partner_referrals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)
    partner_organization_id = Column(UUID(as_uuid=True), ForeignKey("partner_organizations.id"), nullable=False)
    routing_category = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")
    notes = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class PropertyAsset(Base):
    __tablename__ = "property_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True, index=True)

    property_address = Column(String, nullable=False)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    acquisition_cost = Column(Float, nullable=True)
    estimated_value = Column(Float, nullable=True)
    loan_amount = Column(Float, nullable=True)
    tenant_homeowner_id = Column(UUID(as_uuid=True), nullable=True)
    lease_terms = Column(String, nullable=True)
    equity_share_percentage = Column(Float, nullable=True)
    portfolio_status = Column(String, nullable=True, default="active")

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class MembershipProfile(Base):
    __tablename__ = "membership_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    membership_status = Column(String, nullable=False, default="active")
    membership_type = Column(String, nullable=False, default="cooperative")
    equity_share = Column(Float, nullable=False, default=0.0)
    voting_power = Column(Float, nullable=False, default=1.0)
    join_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ForeclosureLeadImport(Base):
    __tablename__ = "foreclosure_lead_imports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String, nullable=False)
    import_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    property_address = Column(String, nullable=False)
    foreclosure_stage = Column(String, nullable=True)


class TrainingGuideStep(Base):
    __tablename__ = "training_guide_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_id = Column(String, nullable=False, unique=True)
    step_title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    related_endpoint = Column(String, nullable=False)
    role_required = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
