from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.sql import func

from .base import Base


# ============================================================
# ENUM DEFINITIONS
# ============================================================

class ApplicationStatus(enum.Enum):
    started = "started"
    submitted = "submitted"
    needs_info = "needs_info"
    qualified = "qualified"
    not_qualified = "not_qualified"


class MembershipStatus(enum.Enum):
    active = "active"
    paused = "paused"
    expired = "expired"
    cancelled = "cancelled"


class InstallmentStatus(enum.Enum):
    due = "due"
    paid_cash = "paid_cash"
    satisfied_contribution = "satisfied_contribution"
    missed = "missed"
    waived = "waived"


class CreditType(enum.Enum):
    testimonial_video = "testimonial_video"
    referral = "referral"
    volunteer = "volunteer"
    training_module = "training_module"
    other = "other"


class CheckinType(enum.Enum):
    hardship_notice = "hardship_notice"
    monthly_update = "monthly_update"
    support_request = "support_request"


# ============================================================
# APPLICATION
# ============================================================

class Application(Base):
    __tablename__ = "applications"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    email = Column(Text, nullable=False)
    full_name = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)

    program_key = Column(Text, nullable=False, index=True)

    status = Column(
        ENUM(ApplicationStatus, name="applicationstatus", create_type=False),
        nullable=False,
    )

    answers_json = Column(JSONB, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    submitted_at = Column(DateTime(timezone=True), nullable=True)


# ============================================================
# MEMBERSHIP
# ============================================================

class Membership(Base):
    __tablename__ = "memberships"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    program_key = Column(Text, nullable=False, index=True)

    term_start = Column(Date, nullable=False)
    term_end = Column(Date, nullable=False)

    annual_price_cents = Column(Integer, nullable=False)
    installment_cents = Column(Integer, nullable=False)

    status = Column(
        ENUM(MembershipStatus, name="membershipstatus", create_type=False),
        nullable=False,
        server_default="active",
    )

    good_standing = Column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


# ============================================================
# MEMBERSHIP INSTALLMENTS
# ============================================================

class MembershipInstallment(Base):
    __tablename__ = "membership_installments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    membership_id = Column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id"),
        nullable=False,
        index=True,
    )

    due_date = Column(Date, nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False)

    status = Column(
        ENUM(InstallmentStatus, name="installmentstatus", create_type=False),
        nullable=False,
        server_default="due",
    )

    paid_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


# ============================================================
# STABILITY ASSESSMENT
# ============================================================

class StabilityAssessment(Base):
    __tablename__ = "stability_assessments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    property_id = Column(
        UUID(as_uuid=True),
        ForeignKey("properties.id"),
        nullable=True,
    )

    program_key = Column(Text, nullable=False, index=True)

    equity_estimate = Column(Numeric(12, 2), nullable=True)
    equity_health_band = Column(Text, nullable=True)

    stability_score = Column(Integer, nullable=False)
    risk_level = Column(Text, nullable=True)

    breakdown_json = Column(JSONB, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
