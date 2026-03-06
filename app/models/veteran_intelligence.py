from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class VeteranProfile(Base):
    __tablename__ = "veteran_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, unique=True, index=True)

    branch_of_service = Column(String, nullable=True)
    years_of_service = Column(Integer, nullable=True)
    discharge_status = Column(String, nullable=True)
    disability_rating = Column(Integer, nullable=True)
    permanent_and_total_status = Column(Boolean, nullable=False, default=False)
    combat_service = Column(Boolean, nullable=False, default=False)
    dependent_status = Column(Boolean, nullable=False, default=False)
    state_of_residence = Column(String, nullable=True)
    homeowner_status = Column(Boolean, nullable=False, default=False)
    mortgage_status = Column(String, nullable=True)
    foreclosure_risk = Column(Boolean, nullable=False, default=False)
    income_level = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BenefitRegistry(Base):
    __tablename__ = "benefit_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    benefit_name = Column(String, nullable=False, unique=True)
    eligibility_rules = Column(JSON, nullable=False)
    required_documents = Column(JSON, nullable=False)
    estimated_value = Column(Float, nullable=True)
    application_steps = Column(JSON, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BenefitProgress(Base):
    __tablename__ = "benefit_progress"
    __table_args__ = (
        UniqueConstraint("case_id", "benefit_name", name="uq_benefit_progress_case_benefit"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)
    benefit_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="NOT_STARTED")
    status_notes = Column(String, nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BenefitDiscoveryAggregate(Base):
    __tablename__ = "benefit_discovery_aggregates"
    __table_args__ = (
        UniqueConstraint("state_of_residence", "benefit_name", name="uq_benefit_aggregate_state_benefit"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state_of_residence = Column(String, nullable=False)
    benefit_name = Column(String, nullable=False)
    discovery_count = Column(Integer, nullable=False, default=0)
    last_discovered_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
