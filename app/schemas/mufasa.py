from pydantic import BaseModel


class MufasaChatRequest(BaseModel):
    prompt: str


class MufasaChatResponse(BaseModel):
    response: str
    actions_executed: list[str]
    results: dict
