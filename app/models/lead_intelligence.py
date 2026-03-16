from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base


class LeadSource(Base):
    __tablename__ = "lead_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_name = Column(String, nullable=False, unique=True)
    source_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class PropertyLead(Base):
    __tablename__ = "property_leads"
    __table_args__ = (
        UniqueConstraint("source_id", "property_address", name="uq_property_leads_source_address"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("lead_sources.id"), nullable=True, index=True)
    property_address = Column(String, nullable=False)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    foreclosure_stage = Column(String, nullable=True)
    tax_delinquent = Column(String, nullable=True)
    equity_estimate = Column(Float, nullable=True)
    auction_date = Column(DateTime(timezone=True), nullable=True)
    owner_occupancy = Column(String, nullable=True)
    raw_payload = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class LeadScore(Base):
    __tablename__ = "lead_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("property_leads.id"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    grade = Column(String, nullable=False)
    recommended_action = Column(String, nullable=True)
    created_case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
