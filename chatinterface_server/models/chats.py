from typing import Annotated
from pydantic import BaseModel, Field

class ComposeMessage(BaseModel):
    recipient: Annotated[str, Field(max_length=20, description="Recipient username")]
    message_data: str


class SendMessage(BaseModel):
    recipient: Annotated[str, Field(max_length=20, description="Recipient username")]
    message_data: str


class EditMessage(BaseModel):
    message_data: str


class DeleteMessage(BaseModel):
    message_id: str
