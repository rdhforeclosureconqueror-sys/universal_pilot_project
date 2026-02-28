from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class WorkflowStepDTO(BaseModel):
    step_key: str
    label: str

    model_config = ConfigDict(from_attributes=True)


class InstallmentDTO(BaseModel):
    due_date: date
    amount_cents: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class MemberDashboardResponse(BaseModel):
    membership_status: str
    good_standing: bool
    stability_score: int
    risk_level: Optional[str]
    next_workflow_step: Optional[WorkflowStepDTO]
    next_installment: Optional[InstallmentDTO]

    model_config = ConfigDict(from_attributes=True)


MemberDashboardDTO = MemberDashboardResponse
