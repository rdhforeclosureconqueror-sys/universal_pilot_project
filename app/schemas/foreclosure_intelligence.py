from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ForeclosureCreateRequest(BaseModel):
    case_id: Optional[UUID] = None
    property_address: str
    city: str
    state: str
    loan_balance: float
    estimated_property_value: float
    arrears_amount: float
    foreclosure_stage: str
    zip_code: Optional[str] = None
    monthly_payment: Optional[float] = None
    lender_name: Optional[str] = None
    servicer_name: Optional[str] = None
    occupancy_status: Optional[str] = None
    homeowner_income: Optional[float] = 0
    homeowner_hardship_reason: Optional[str] = None
    full_name: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    consent_acknowledged: Optional[bool] = False
    timeline_notes: Optional[str] = None
    lead_id: Optional[UUID] = None
    program_key: Optional[str] = None


class ForeclosureAnalyzeRequest(BaseModel):
    case_id: Optional[UUID] = None
    estimated_property_value: float
    loan_balance: float
    arrears_amount: float
    homeowner_income: Optional[float] = 0
    foreclosure_stage: str
