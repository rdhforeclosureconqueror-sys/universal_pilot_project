from pydantic import BaseModel
from typing import List, Dict, Any


class MufasaChatRequest(BaseModel):
    prompt: str
    investor_mode: bool = False


class MufasaChatResponse(BaseModel):
    response: str
    actions_executed: List[str]
    results: Dict[str, Any]


class MufasaExplainResponse(BaseModel):
    explanation: str
