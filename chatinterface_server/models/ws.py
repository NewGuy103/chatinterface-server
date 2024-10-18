from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict
from fastapi import WebSocket

class MessageData(BaseModel):
    message: str
    data: dict


class ChatMessageSend(BaseModel):
    recipient: Annotated[str, Field(max_length=20, description="Recipient username")]
    data: str
    id: str


class ClientInfo(BaseModel):
    ws: WebSocket
    ip: str
    username: str
    token: str

    model_config = ConfigDict(arbitrary_types_allowed=True)
