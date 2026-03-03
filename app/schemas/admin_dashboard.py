from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminMembershipRow(BaseModel):
    membership_id: UUID
    user_id: UUID
    email: Optional[str]
    full_name: Optional[str]
    program_key: str
    status: str
    good_standing: bool
    term_start: date
    term_end: date
    created_at: datetime
    latest_stability_score: Optional[int]
    latest_stability_at: Optional[datetime]
    missed_installments_count: int
    due_installments_count: int
    last_activity_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class AdminMembershipListResponse(BaseModel):
    items: list[AdminMembershipRow]
    limit: int
    offset: int


class AdminMembershipDetailResponse(BaseModel):
    membership: AdminMembershipRow
    installments: list[dict[str, Any]]
    stability_history: list[dict[str, Any]]
    member_checkins: list[dict[str, Any]]
    contribution_credits: list[dict[str, Any]]
    workflow: Optional[dict[str, Any]]
