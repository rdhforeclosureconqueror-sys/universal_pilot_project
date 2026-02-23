from sqlalchemy import Column, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from models.enums import DocumentType
from .base import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), nullable=False)
    doc_type = Column(
        Enum(DocumentType, name="documenttype", create_type=False),
        nullable=False,
    )
    meta = Column(JSON, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
