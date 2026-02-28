from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class BotSettingUpsert(BaseModel):
    key: str
    value: str


class BotReportCreate(BaseModel):
    bot: str
    level: str
    code: Optional[str] = None
    message: str
    details_json: Optional[dict[str, Any]] = None


class BotReportRead(BotReportCreate):
    id: UUID
    created_at: datetime


class BotCommandCreate(BaseModel):
    target_bot: str
    command: str
    args_json: Optional[dict[str, Any]] = None
    priority: int = 10
    status: Optional[str] = None
    notes: Optional[str] = None


class BotCommandRead(BotCommandCreate):
    id: UUID
    created_at: datetime


class BotTriggerCreate(BaseModel):
    enabled: bool = True
    metric: str
    operator: str = ">="
    threshold: float = 0
    priority: int = 10
    target_bot: str
    command: str
    args_json: Optional[dict[str, Any]] = None


class BotTriggerRead(BotTriggerCreate):
    id: UUID


class BotInboundLogCreate(BaseModel):
    source_bot: str
    payload_hash: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    raw_json: Optional[dict[str, Any]] = None


class BotInboundLogRead(BotInboundLogCreate):
    id: UUID
    created_at: datetime


class BotPageCreate(BaseModel):
    url: str
    status: Optional[str] = None
    last_crawl: Optional[datetime] = None
    title: Optional[str] = None
    notes: Optional[str] = None


class BotPageRead(BotPageCreate):
    id: UUID


class LeadUpsert(BaseModel):
    lead_id: Optional[str] = None
    source: Optional[str] = None
    address: str
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    apn: Optional[str] = None
    county: Optional[str] = None
    trustee: Optional[str] = None
    mortgagor: Optional[str] = None
    mortgagee: Optional[str] = None
    auction_date: Optional[datetime] = None
    case_number: Optional[str] = None
    opening_bid: Optional[float] = None
    list_price: Optional[float] = None
    arrears: Optional[float] = None
    equity_pct: Optional[float] = None
    arv: Optional[float] = None
    mao: Optional[float] = None
    spread_pct: Optional[float] = None
    tier: Optional[str] = None
    south_dallas_override: bool = False
    exit_strategy: Optional[str] = None
    status: Optional[str] = None
    score: Optional[float] = None
    notes: Optional[str] = None


class LeadRead(LeadUpsert):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
