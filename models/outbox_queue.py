from sqlalchemy import Column, String, DateTime, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from .base import Base

class OutboxQueue(Base):
    __tablename__ = "outbox_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String)
    case_id = Column(UUID(as_uuid=True))
    payload = Column(JSON)
    dedupe_key = Column(String, unique=True)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
