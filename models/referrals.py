from sqlalchemy import Column, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from models.enums import ReferralStatus
from .base import Base

class Referral(Base):
    __tablename__ = "referrals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    status = Column(
        Enum(ReferralStatus, name="referralstatus", create_type=False),
        nullable=False,
        default="draft",
    )
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
