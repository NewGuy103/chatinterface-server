from pydantic import BaseModel, ConfigDict
from fastapi import WebSocket

class MessageData(BaseModel):
    message: str
    data: dict


class ClientInfo(BaseModel):
    ws: WebSocket
    ip: str
    username: str
    token: str

    model_config = ConfigDict(arbitrary_types_allowed=True)
