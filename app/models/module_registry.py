from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class ModuleRegistry(Base):
    __tablename__ = "module_registry"
    __table_args__ = (
        UniqueConstraint("module_name", "version", name="uq_module_registry_name_version"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_name = Column(String, nullable=False)
    module_type = Column(String, nullable=False)
    version = Column(String, nullable=False, default="1.0.0")

    permissions = Column(JSON, nullable=False)
    required_services = Column(JSON, nullable=False)
    data_schema = Column(JSON, nullable=False)
    allowed_actions = Column(JSON, nullable=False)

    status = Column(String, nullable=False, default="draft")
    validation_errors = Column(JSON, nullable=True)
    policy_validation_status = Column(String, nullable=False, default="pending")
    is_active = Column(Boolean, nullable=False, default=False)
    activated_at = Column(DateTime(timezone=True), nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
