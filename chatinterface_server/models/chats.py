import uuid
from typing import Annotated
from pydantic import BaseModel, Field

class ComposeMessage(BaseModel):
    recipient: Annotated[str, Field(max_length=20, description="Recipient username")]
    message_data: Annotated[str, Field(max_length=2000, min_length=1)]


class SendMessage(BaseModel):
    recipient: Annotated[str, Field(max_length=20, description="Recipient username")]
    message_data: Annotated[str, Field(max_length=2000, min_length=1)]


class EditMessage(BaseModel):
    message_data: Annotated[str, Field(max_length=2000, min_length=1)]


class DeleteMessage(BaseModel):
    message_id: uuid.UUID


class MessagesGetPublic(BaseModel):
    sender_name: Annotated[str, Field(max_length=20, min_length=1)]
    message_data: Annotated[str, Field(max_length=2000, min_length=1)]
    send_date: Annotated[str, Field(description="Datetime in YYYY-MM-DD H:M:S.ffffff format.")] 
    message_id: uuid.UUID
