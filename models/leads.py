from sqlalchemy import Column, String, Float, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base  # Make sure this points to your declarative base

import uuid

class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(String, nullable=False, unique=True)
    source = Column(String)
    address = Column(String, nullable=False)
    city = Column(String)
    state = Column(String)
    zip = Column(String)
    apn = Column(String)
    county = Column(String)
    trustee = Column(String)
    mortgagor = Column(String)
    mortgagee = Column(String)
    auction_date = Column(DateTime(timezone=True))
    case_number = Column(String)
    opening_bid = Column(Float)
    list_price = Column(Float)
    arrears = Column(Float)
    equity_pct = Column(Float)
    arv = Column(Float)
    mao = Column(Float)
    spread_pct = Column(Float)
    tier = Column(String)
    south_dallas_override = Column(Boolean, nullable=False, default=False)
    exit_strategy = Column(String)
    status = Column(String)
    score = Column(Float)
    notes = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
