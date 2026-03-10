from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base


class AICommandLog(Base):
    __tablename__ = "ai_command_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    message = Column(String, nullable=False)
    ai_response = Column(String, nullable=False)
    actions_triggered = Column(JSONB, nullable=False, default=list)
    results = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
