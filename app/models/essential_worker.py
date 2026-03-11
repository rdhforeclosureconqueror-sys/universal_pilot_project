from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base


class EssentialWorkerProfile(Base):
    __tablename__ = "essential_worker_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    profession = Column(String, nullable=False)
    employer_type = Column(String, nullable=True)
    state = Column(String, nullable=False)
    city = Column(String, nullable=True)
    annual_income = Column(Float, nullable=True)
    first_time_homebuyer = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EssentialWorkerBenefitMatch(Base):
    __tablename__ = "essential_worker_benefit_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("essential_worker_profiles.id"), nullable=False, index=True)
    program = Column(String, nullable=False)
    estimated_value = Column(Float, nullable=False)
    details = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
