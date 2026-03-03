from pydantic import BaseModel


class AIMessageRequest(BaseModel):
    message: str


class AIExecuteRequest(BaseModel):
    message: str
    confirm: bool = False


class AIVoiceResponse(BaseModel):
    transcript: str
    advisory: dict
    execution: dict | None = None
    audio_response_b64: str
