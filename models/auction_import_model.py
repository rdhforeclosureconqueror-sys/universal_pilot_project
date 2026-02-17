from sqlalchemy import Column, String, Integer, DateTime, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base

class AuctionImport(Base):
    __tablename__ = "auction_imports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    file_bytes = Column(LargeBinary, nullable=False)
    file_type = Column(String, nullable=True)
    status = Column(String, nullable=False, default="received")
    records_created = Column(Integer, nullable=False, default=0)
    error_message = Column(String, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
