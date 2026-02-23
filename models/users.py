from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from .base import Base

class UserRole(enum.Enum):
    case_worker = "case_worker"
    referral_coordinator = "referral_coordinator"
    admin = "admin"
    audit_steward = "audit_steward"
    ai_policy_chair = "ai_policy_chair"
    partner_org = "partner_org"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(
        Enum(UserRole, name="userrole", create_type=False),
        nullable=False,
    )
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
