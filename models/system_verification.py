import uuid

from sqlalchemy import Boolean, Column, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from .base import Base


# ============================================================
# SYSTEM PHASE
# ============================================================

class SystemPhase(Base):
    __tablename__ = "system_phases"

    __table_args__ = (
        UniqueConstraint(
            "environment",
            "phase_key",
            name="uq_system_phases_environment_phase_key",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    environment = Column(String(20), nullable=False, index=True)
    phase_key = Column(String(100), nullable=False, index=True)

    status = Column(String(20), nullable=False)

    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


# ============================================================
# PHASE VERIFICATION RUN
# ============================================================

class PhaseVerificationRun(Base):
    __tablename__ = "phase_verification_runs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    environment = Column(String(20), nullable=False, index=True)
    phase_key = Column(String(100), nullable=False, index=True)

    result = Column(JSONB, nullable=False)
    success = Column(Boolean, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
