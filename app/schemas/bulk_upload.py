# schemas/bulk_upload.py

from typing import List, Dict, Optional
from pydantic import BaseModel

class SingleCaseDraft(BaseModel):
    meta: Dict[str, str]

class BulkUploadRequest(BaseModel):
    program_key: str
    created_by: str  # user_id
    cases: List[SingleCaseDraft]
