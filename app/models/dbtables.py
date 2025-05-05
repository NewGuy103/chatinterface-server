import uuid
import secrets

from datetime import datetime
from sqlmodel import Relationship, SQLModel, Field


class UserBase(SQLModel, table=False):
    user_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(max_length=20, nullable=False, unique=True, index=True)
    hashed_password: str = Field(max_length=100, nullable=False)


class Users(UserBase, table=True):
    sessions: list['UserSessions'] = Relationship(
        back_populates='user', 
        sa_relationship_kwargs={'lazy': 'selectin'},
        passive_deletes='all'
    )
    sender_messages: list['Messages']= Relationship(
        back_populates='sender', 
        sa_relationship_kwargs={'lazy': 'selectin', 'foreign_keys': '[Messages.sender_id]'},
        passive_deletes='all'
    )
    recipient_messages: list['Messages']= Relationship(
        back_populates='recipient', 
        sa_relationship_kwargs={'lazy': 'selectin', 'foreign_keys': '[Messages.recipient_id]'},
        passive_deletes='all'
    )


class UserSessions(SQLModel, table=True):
    session_id: str = Field(
        primary_key=True, 
        max_length=45, 
        default_factory=lambda: secrets.token_urlsafe(32)
    )
    user_id: uuid.UUID = Field(foreign_key='users.user_id', ondelete='CASCADE')

    expires_on: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.now)

    user: Users = Relationship(
        back_populates='sessions', 
        sa_relationship_kwargs={'lazy': 'selectin'}
    )


# Uses two foreign keys tied to the Users table
class Messages(SQLModel, table=True):
    message_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sender_id: uuid.UUID = Field(foreign_key='users.user_id', ondelete='CASCADE')

    recipient_id: uuid.UUID = Field(foreign_key='users.user_id', ondelete='CASCADE')
    send_date: datetime = Field(default_factory=datetime.now, index=True)

    message_data: str = Field(max_length=2000, min_length=1)
    sender: Users = Relationship(
        back_populates='sender_messages',
        sa_relationship_kwargs={'lazy': 'selectin', 'foreign_keys': '[Messages.sender_id]'},
    )

    recipient: Users = Relationship(
        back_populates='recipient_messages',
        sa_relationship_kwargs={'lazy': 'selectin', 'foreign_keys': '[Messages.recipient_id]'},
    )
