from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func
import uuid
from app.models.enums import CaseStatus
from .base import Base


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        UniqueConstraint("property_id", "auction_date", name="uq_cases_property_auction_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(
        ENUM(
            CaseStatus,
            name="casestatus",
            create_type=False
        ),
        nullable=False
    ) 
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Runtime-aligned fields used by API routes/policy logic
    program_type = Column(String, nullable=True)
    program_key = Column(String, nullable=True)
    meta = Column(JSON, nullable=True)

    case_type = Column(String, nullable=True)
    meta = Column(JSON, nullable=True)
    policy_version_id = Column(UUID(as_uuid=True), ForeignKey("policy_versions.id"))
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=True)
    auction_date = Column(DateTime(timezone=True), nullable=True)
    canonical_key = Column(String, nullable=True, unique=True, index=True)
