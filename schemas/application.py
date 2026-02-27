from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ApplicationCreate(BaseModel):
    email: str
from pydantic import BaseModel, Field


class ApplicationCreate(BaseModel):
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    program_key: str
    answers_json: Dict[str, Any] = Field(default_factory=dict)


class ApplicationResponse(BaseModel):
    id: str
    status: str
    created_at: datetime
