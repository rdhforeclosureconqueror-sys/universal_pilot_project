from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from .base import Base

class CertRevocation(Base):
    __tablename__ = "cert_revocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certification_id = Column(UUID(as_uuid=True), ForeignKey("certifications.id"))
    reason_code = Column(String, nullable=False)
    revoked_by_system = Column(Boolean, default=True)
    revoked_at = Column(DateTime(timezone=True), server_default=func.now())
