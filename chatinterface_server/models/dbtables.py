import uuid
import secrets

from datetime import datetime
from sqlmodel import SQLModel, Field


class Users(SQLModel, table=True):
    user_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(max_length=20, nullable=False, unique=True, index=True)
    hashed_password: str = Field(max_length=100, nullable=False)


class UserSessions(SQLModel, table=True):
    session_id: str = Field(
        primary_key=True, 
        max_length=45, 
        default_factory=lambda: secrets.token_urlsafe(32)
    )
    user_id: uuid.UUID = Field(foreign_key='users.user_id', ondelete='CASCADE')
    expires_on: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.now)


class Messages(SQLModel, table=True):
    message_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sender_id: uuid.UUID = Field(foreign_key='users.user_id', ondelete='CASCADE')

    recipient_id: uuid.UUID = Field(foreign_key='users.user_id', ondelete='CASCADE')
    send_date: datetime = Field(default_factory=datetime.now, index=True)

    message_data: str = Field(max_length=2000, min_length=1)


class UserChatRelations(SQLModel, table=True):
    sender_id: uuid.UUID = Field(primary_key=True, foreign_key='users.user_id', ondelete='CASCADE')
    recipient_id: uuid.UUID = Field(foreign_key='users.user_id', ondelete='CASCADE')


class UserInstance(Users, table=False):
    pass
