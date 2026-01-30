from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base


class DealScore(Base):
    __tablename__ = "deal_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    score = Column(Integer, nullable=False)
    tier = Column(String, nullable=False)
    exit_strategy = Column(String, nullable=False)
    urgency_days = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
