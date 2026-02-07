from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from models.enums import CaseStatus
from .base import Base

class Case(Base):
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(Enum(CaseStatus), nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    program_type = Column(String, nullable=True)
    program_key = Column(String, nullable=True)
    case_type = Column(String, nullable=True)
    meta = Column(JSON, nullable=True)
    policy_version_id = Column(UUID(as_uuid=True), ForeignKey("policy_versions.id"))
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=True)
