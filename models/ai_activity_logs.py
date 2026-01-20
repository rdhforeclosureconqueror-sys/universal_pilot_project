from sqlalchemy import Column, String, DateTime, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from .base import Base

class AIActivityLog(Base):
    __tablename__ = "ai_activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True))
    policy_version_id = Column(UUID(as_uuid=True))
    ai_role = Column(String)
    model_provider = Column(String)
    model_name = Column(String)
    model_version = Column(String)
    prompt_hash = Column(String)
    policy_rule_id = Column(String)
    confidence_score = Column(Numeric(5, 4))
    human_override = Column(Boolean, default=False)
    incident_type = Column(String, nullable=True)
    admin_review_required = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
