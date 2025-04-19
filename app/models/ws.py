import uuid
from typing import Annotated
from pydantic import BaseModel, Field


UsernameField = Annotated[str, Field(max_length=20, min_length=1)]
MessageDataField = Annotated[str, Field(max_length=2000, min_length=1)]


class MessageData(BaseModel):
    message: str
    data: dict


class MessageUpdate(BaseModel):
    message_id: uuid.UUID
    message_data: MessageDataField
    sender_name: UsernameField
    recipient_name: UsernameField


class MessageDelete(BaseModel):
    message_id: uuid.UUID
    sender_name: UsernameField
    recipient_name: UsernameField
