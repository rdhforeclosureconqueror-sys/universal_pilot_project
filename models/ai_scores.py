from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from .base import Base


class AIScore(Base):
    __tablename__ = "ai_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    equity = Column(Numeric(12, 2), nullable=False)
    strategy = Column(String, nullable=False)
    confidence = Column(Numeric(4, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
