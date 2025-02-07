import uuid
from typing import Annotated
from pydantic import BaseModel, Field


UsernameField = Annotated[str, Field(max_length=20, min_length=1)]
MessageDataField = Annotated[str, Field(max_length=2000, min_length=1)]

class ComposeMessage(BaseModel):
    recipient: UsernameField
    message_data: MessageDataField


class SendMessage(BaseModel):
    recipient: UsernameField
    message_data: MessageDataField


class EditMessage(BaseModel):
    message_data: MessageDataField


class DeleteMessage(BaseModel):
    message_id: uuid.UUID


class MessagesGetPublic(BaseModel):
    sender_name: UsernameField
    recipient_name: UsernameField
    message_data: MessageDataField
    send_date: Annotated[str, Field(description="Datetime in YYYY-MM-DD H:M:S.ffffff format.")] 
    message_id: uuid.UUID
