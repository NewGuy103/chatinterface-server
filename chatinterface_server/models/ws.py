from pydantic import BaseModel

class MessageData(BaseModel):
    message: str
    data: dict
