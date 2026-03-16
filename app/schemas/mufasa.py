from pydantic import BaseModel


class MufasaChatRequest(BaseModel):
    prompt: str
    investor_mode: bool = False


class MufasaChatResponse(BaseModel):
    response: str
    actions_executed: list[str]
    results: dict


class MufasaExplainResponse(BaseModel):
    explanation: str
