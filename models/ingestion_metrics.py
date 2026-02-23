import uuid

from sqlalchemy import Column, String, DateTime, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .base import Base


class IngestionMetric(Base):
    __tablename__ = "ingestion_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_type = Column(String, nullable=False, index=True)
    source = Column(String, nullable=True)
    file_hash = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    count_value = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
