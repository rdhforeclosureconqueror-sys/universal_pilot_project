from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from .base import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String, unique=True, index=True, nullable=False)

    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    zip = Column(String, nullable=False)
    county = Column(String, nullable=True)

    property_type = Column(String, nullable=True)
    year_built = Column(Integer, nullable=True)
    sqft = Column(Integer, nullable=True)
    beds = Column(Float, nullable=True)
    baths = Column(Float, nullable=True)

    assessed_value = Column(Integer, nullable=True)

    mortgagor = Column(String, nullable=True)
    mortgagee = Column(String, nullable=True)
    trustee = Column(String, nullable=True)

    loan_type = Column(String, nullable=True)
    interest_rate = Column(Float, nullable=True)
    orig_loan_amount = Column(Integer, nullable=True)
    est_balance = Column(Integer, nullable=True)

    auction_date = Column(DateTime(timezone=False), nullable=True)
    auction_time = Column(String, nullable=True)

    source = Column(String, nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
