from typing import Any, Dict, Optional
from pydantic import BaseModel


class CaseCreateRequest(BaseModel):
    program_key: str
    created_by: str
    meta: Optional[Dict[str, Any]] = None
