from pydantic import BaseModel, ConfigDict, Field


class VeteranProfileIn(BaseModel):
    case_id: str
    branch_of_service: str | None = None
    years_of_service: int | None = None
    discharge_status: str | None = None
    disability_rating: int = Field(default=0, ge=0, le=100)
    permanent_and_total_status: bool = False
    combat_service: bool = False
    dependent_status: bool = False
    state_of_residence: str | None = None
    homeowner_status: bool = False
    mortgage_status: str | None = None
    foreclosure_risk: bool = False
    income_level: str | None = None


class BenefitMatchResult(BaseModel):
    eligible_benefits: list[str]
    estimated_total_value: float
    priority_order: list[str]


class BenefitActionPlan(BaseModel):
    steps: list[str]


class BenefitProgressUpdate(BaseModel):
    case_id: str
    benefit_name: str
    status: str
    status_notes: str | None = None


class VeteranAdvisoryRequest(BaseModel):
    case_id: str
    question: str


class PartnerBenefitAggregateRead(BaseModel):
    state_of_residence: str
    benefit_name: str
    discovery_count: int

    model_config = ConfigDict(from_attributes=True)
