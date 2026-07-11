from pydantic import BaseModel, model_validator
from fastapi import Request
from typing import Dict, Optional, Any
from const import * 

class TTSRequest(BaseModel):
    text: str
    list_voice: list = VOICE_LIST
    voice: str = "Jasper" 
    speed: float = 1.0
    name: str = 'output'

class RequestInfo(BaseModel):
    method: str
    url: str
    headers: Dict[str, str]
    client: Dict[str, Optional[str]]  # Captures host and port

    @model_validator(mode='before')
    @classmethod
    def from_request(cls, data: Any) -> Any:
        if isinstance(data, Request):
            return {
                "method": data.method,
                "url": str(data.url),
                "headers": dict(data.headers),
                "client": {
                    "host": data.client.host if data.client else None,
                    "port": str(data.client.port) if data.client else None
                },
            }
        return data