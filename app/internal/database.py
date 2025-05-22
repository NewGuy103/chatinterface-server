import asyncio
import secrets
import logging
import uuid

import argon2  # argon2-cffi

from datetime import datetime
from functools import wraps, partial
from concurrent.futures import ThreadPoolExecutor
from sqlmodel import Session, and_, desc, or_, select, create_engine
from sqlalchemy import Engine

from .constants import DBReturnCodes
from .config import settings
from ..models.dbtables import (
    Users, UserSessions, Messages
)
from ..models.chats import MessagesGetPublic

logger: logging.Logger = logging.getLogger("chatinterface_server")
engine = create_engine(str(settings.SQLALCHEMY_ENGINE_URI))


def async_threaded(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        partial_func: partial = partial(func, self, *args, **kwargs)
        
        try:
            return await loop.run_in_executor(self.executor, partial_func) 
        except Exception:
            func_name: str = func.__name__
            logger.exception("Database call failed on function [%s]:", func_name)
            raise
    
    return wrapper


class MainDatabase:
    def __init__(self, engine: Engine) -> None:
        self.engine: Engine = engine
        self.pw_hasher: argon2.PasswordHasher = argon2.PasswordHasher()

        self.executor: ThreadPoolExecutor = ThreadPoolExecutor()

    def override_engine(self, engine: Engine):
        """Override SQLAlchemy engine for tests."""
        self.engine = engine
    
    @async_threaded
    def setup(self):
        # Let the schema creation be handled by alembic
        # SQLModel.metadata.create_all(self.engine)
        statement = select(Users).where(Users.username == settings.FIRST_USER_NAME)

        with Session(self.engine) as session:
            result = session.exec(statement)

            if not result.one_or_none():
                user_id: uuid.UUID = uuid.uuid4()
                hashed_pw: str = self.pw_hasher.hash(settings.FIRST_USER_PASSWORD)
                first_user: Users = Users(
                    user_id=user_id, 
                    username=settings.FIRST_USER_NAME, 
                    hashed_password=hashed_pw
                )

                session.add(first_user)
                session.commit()
        
        self.messages = ChatMethods(self)
        self.users = UserMethods(self)

    def get_user(self, session: Session, username: str) -> Users | None:
        statement = select(Users).where(Users.username == username)
        
        result = session.exec(statement)
        user: Users | None = result.one_or_none()

        if not user:
            return None

        return user
    
    def close(self):
        self.executor.shutdown()
        self.engine.dispose()


class UserMethods:
    def __init__(self, parent: MainDatabase) -> None:
        self.parent: MainDatabase = parent
        self.engine = parent.engine

        self.pw_hasher = parent.pw_hasher

        self.get_user = parent.get_user
        self.executor = parent.executor

    @async_threaded
    def add_user(self, session: Session, username: str, password: str) -> str | bool:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        if not isinstance(password, str):
            raise TypeError("password is not a string")

        if len(username) > 20:
            raise ValueError("username is too long (over 20 characters)")
        
        user: Users | None = self.get_user(session, username)
        if user:
            return DBReturnCodes.USER_EXISTS

        hashed_pw: str = self.pw_hasher.hash(password)
        new_user: Users = Users(username=username, hashed_password=hashed_pw)

        session.add(new_user)
        session.commit()

        return True

    @async_threaded
    def delete_user(self, session: Session, username: str) -> str | bool:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        if len(username) > 20:
            raise ValueError("username is too long (over 20 characters)")
        
        user: Users = self.get_user(session, username)
        if not user:
            return DBReturnCodes.NO_USER

        user: Users = session.exec(
            select(Users).where(Users.user_id == user.user_id)
        ).one()

        session.delete(user)
        session.commit()

        return True

    @async_threaded
    def get_users(self, session: Session) -> list:
        result = session.exec(select(Users))
        users = result.all()

        user_list: list[str] = []
        for user in users:
            user_list.append(user.username)
        
        return user_list

    @async_threaded
    def verify_user(self, session: Session, username: str, password: str) -> str | int:
        if not isinstance(username, str):
            raise TypeError("username is not a string")
        
        if not isinstance(password, str):
            raise TypeError("password is not a string")
        
        statement = select(Users).where(Users.username == username)

        result = session.exec(statement)
        user: Users | None = result.one_or_none()

        if not user:
            return DBReturnCodes.NO_USER
        
        try:
            self.pw_hasher.verify(user.hashed_password, password)
        except (argon2.exceptions.VerificationError, argon2.exceptions.VerifyMismatchError):
            return DBReturnCodes.INVALID_TOKEN
        except Exception:
            logger.exception("Failed to verify password:")
            raise
        
        return 0

    @async_threaded
    def create_session(self, session: Session, username: str, expires_on: str) -> str:
        if not isinstance(username, str):
            raise TypeError("username is not a string")
        
        if not isinstance(expires_on, str):
            raise TypeError("expires_on is not a string")

        expiry_date: datetime = datetime.strptime(expires_on, "%Y-%m-%d %H:%M:%S")        
        date_today: datetime = datetime.now()

        if date_today > expiry_date:
            raise ValueError("provided date is in the past")

        user: Users = self.get_user(session, username)
        if not user:
            raise ValueError("current provided username is invalid")

        session_token: str = secrets.token_urlsafe(32)
        new_session: UserSessions = UserSessions(
            session_id=session_token,
            user_id=user.user_id, 
            expires_on=expiry_date
        )

        session.add(new_session)
        session.commit()

        return session_token

    @async_threaded
    def check_user_exists(self, session: Session, username: str) -> bool:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        user = self.get_user(session, username)
        if user is not None:
            return True

        return False

    def get_sessions(self, session: Session, username: str):
        raise NotImplementedError()

    @async_threaded
    def revoke_session(self, session: Session, session_id: str) -> str:
        if not isinstance(session_id, str):
            raise TypeError("session ID is not a string")

        statement = select(UserSessions).where(UserSessions.session_id == session_id)
        result = session.exec(statement)

        user_session: UserSessions = result.one_or_none()
        if not user_session:
            raise ValueError("current provided session is invalid")

        session.delete(user_session)
        session.commit()

        return True

    @async_threaded
    def get_session_info(self, session: Session, session_id: str) -> dict[str, str | bool] | str:
        if not isinstance(session_id, str):
            raise TypeError("session id is not a string")

        session_statement = select(UserSessions).where(UserSessions.session_id == session_id)

        usersession_result = session.exec(session_statement)
        user_session: UserSessions | None = usersession_result.one_or_none()

        if not user_session:
            raise ValueError("current provided session is invalid")

        user_statement = select(Users).where(Users.user_id == user_session.user_id)
        users_result = session.exec(user_statement)

        user: Users = users_result.one()

        current_date: datetime = datetime.now()
        expired: bool = user_session.expires_on < current_date

        return {
            'created_at': datetime.strftime(user_session.created_at, "%Y-%m-%d %H:%M:%S"),
            'expired': expired,
            'username': user.username,
            'token': session_id
        }

    @async_threaded
    def check_session_expired(self, session: Session, session_id: str) -> bool:
        if not isinstance(session_id, str):
            raise TypeError("session id is not a string")

        statement = select(UserSessions).where(UserSessions.session_id == session_id)
        result = session.exec(statement)
        user_session: UserSessions = result.one_or_none()

        if not user_session:
            return False

        expiry_date: datetime = user_session.expires_on
        current_date: datetime = datetime.now()

        expired: bool = current_date > expiry_date
        return expired


class ChatMethods:
    def __init__(self, parent: MainDatabase) -> None:
        self.parent: MainDatabase = parent
        self.engine = parent.engine

        self.executor = parent.executor
        self.get_user = parent.get_user

    @async_threaded
    def get_chat_relations(self, session: Session, username: str) -> str | set[str]:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        sender_names: set = set()
        recipient_names: set = set()

        user: Users = self.get_user(session, username)
        if not user:
            raise ValueError("current provided username is invalid")
        
        for sender in user.sender_messages:
            sender_names.add(sender.recipient.username)
        
        for recipient in user.recipient_messages:
            recipient_names.add(recipient.sender.username)

        return sender_names | recipient_names

    @async_threaded
    def has_chat_relation(self, session: Session, sender: str, recipient: str) -> bool | str:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")
        
        if not isinstance(recipient, str):
            raise TypeError("recipient username is not a string")

        # Sender is expected to be the current logged in user
        sender_model: Users | None = self.get_user(session, sender)
        if not sender_model:
            raise ValueError('sender provided is invalid')
        
        recipient_model: Users | None = self.get_user(session, recipient)
        if not recipient_model:
            return DBReturnCodes.NO_RECIPIENT
        
        has_sender_relation = session.exec(
            select(Messages)
            .where(
                Messages.sender_id == sender_model.user_id,
                Messages.recipient_id == recipient_model.user_id
            )
            .limit(1)
            .order_by(desc(Messages.send_date))
        ).one_or_none()

        has_recipient_relation = session.exec(
            select(Messages)
            .where(
                Messages.sender_id == recipient_model.user_id,
                Messages.recipient_id == sender_model.user_id
            )
            .limit(1)
            .order_by(desc(Messages.send_date))
        ).one_or_none()

        if has_sender_relation or has_recipient_relation:
            return True
        
        return False

    @async_threaded
    def store_message(self, session: Session, sender: str, recipient: str, message_data: str) -> uuid.UUID | str:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")
        
        if not isinstance(recipient, str):
            raise TypeError("recipient username is not a string")
        
        if not isinstance(message_data, str):
            raise TypeError("message data must be string")

        if len(message_data) < 1:
            raise ValueError("message data must not be empty")

        sender_model: Users = self.get_user(session, sender)
        recipient_model: Users = self.get_user(session, recipient)

        if not sender_model:
            raise ValueError('sender provided is invalid')

        # Covered by has_chat_relation call before this
        if not recipient_model:
            raise ValueError('recipient provided is invalid')

        message_id: uuid.UUID = uuid.uuid4()
        new_message: Messages = Messages(
            message_id=message_id,
            sender_id=sender_model.user_id, 
            recipient_id=recipient_model.user_id,
            message_data=message_data
        )

        session.add(new_message)
        session.commit()

        return message_id

    @async_threaded
    def get_messages(
        self, session: Session, 
        sender: str, recipient: str, 
        amount: int = 100,
        offset: int = 0
    ) -> str | list[MessagesGetPublic]:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")
        
        if not isinstance(recipient, str):
            raise TypeError("recipient username is not a string")
        
        if not isinstance(amount, int):
            raise TypeError("amount must be an int")

        sender_model: Users = self.get_user(session, sender)
        recipient_model: Users = self.get_user(session, recipient)

        if not sender_model:
            raise ValueError("sender provided is invalid")

        if not recipient_model:
            return DBReturnCodes.NO_RECIPIENT

        # Statement in raw SQL
        # SELECT (
        #     SELECT username FROM users
        #     WHERE users.user_id=messages.sender_id
        # ) AS sender_name, message_data, 
        #     DATE_FORMAT(send_date, "%y-%m-%d %h:%m:%S.%f"), message_id

        # FROM messages WHERE (sender_id = %s AND recipient_id = %s)
        # OR (sender_id = %s AND recipient_id = %s)

        # ORDER BY send_date DESC;
        statement = select(Messages).where(
            or_(
                and_(
                    Messages.sender_id == sender_model.user_id, 
                    Messages.recipient_id == recipient_model.user_id
                ),
                and_(
                    Messages.sender_id == recipient_model.user_id,
                    Messages.recipient_id == sender_model.user_id
                )
            )
        ).order_by(desc(Messages.send_date)).limit(amount).offset(offset)
        result = session.exec(statement)

        message_list: list[MessagesGetPublic] = []
        for message in result:
            if message.sender_id == sender_model.user_id:
                sender_name: str = sender_model.username
                recipient_name: str = recipient_model.username
            elif message.sender_id == recipient_model.user_id:
                sender_name: str = recipient_model.username
                recipient_name: str = sender_model.username
            else:
                raise RuntimeError('sender_name invalid')

            message_public: MessagesGetPublic = MessagesGetPublic(
                sender_name=sender_name,
                recipient_name=recipient_name,
                message_data=message.message_data,
                send_date=datetime.strftime(message.send_date, "%Y-%m-%d %H:%M:%S"),
                message_id=str(message.message_id)
            )
            message_list.append(message_public)

        return message_list

    @async_threaded
    def get_message(self, session: Session, sender: str, message_id: uuid.UUID):
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")

        if not isinstance(message_id, uuid.UUID):
            raise TypeError("message_id is not a uuid")

        sender_model: Users = self.get_user(session, sender)
        if not sender_model:
            raise ValueError("sender provided is invalid")

        # Statement in raw SQL
        # SELECT (
        #     SELECT username FROM users
        #     WHERE users.user_id=messages.sender_id
        # ) AS sender_name, message_data, DATE_FORMAT(send_date, "%y-%m-%d %h:%m:%S.%f")

        # FROM messages
        # WHERE message_id=%s AND sender_id=%s
        message: Messages | None = session.exec(
            select(Messages).where(
                Messages.message_id == message_id,
                Messages.sender_id == sender_model.user_id
            )
        ).one_or_none()

        if not message:
            return DBReturnCodes.INVALID_MESSAGE

        return MessagesGetPublic(
            sender_name=sender_model.username,
            recipient_name=message.recipient.username,
            message_data=message.message_data,
            send_date=datetime.strftime(message.send_date, "%Y-%m-%d %H:%M:%S"),
            message_id=str(message.message_id)
        )

    @async_threaded
    def delete_message(self, session: Session, sender: str, message_id: uuid.UUID) -> str | Users:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")

        if not isinstance(message_id, uuid.UUID):
            raise TypeError("message_id is not a uuid")

        sender_model: Users = self.get_user(session, sender)
        if not sender_model:
            raise ValueError('sender provided is invalid')

        message: Messages = session.exec(
            select(Messages).where(
                Messages.message_id == message_id,
                Messages.sender_id == sender_model.user_id
            )
        ).one_or_none()

        if not message:
            return DBReturnCodes.INVALID_MESSAGE

        session.delete(message)
        session.commit()

        return message.recipient

    @async_threaded
    def edit_message(self, session: Session, sender: str, message_id: uuid.UUID, message_data: str) -> str | Users:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")

        if not isinstance(message_id, uuid.UUID):
            raise TypeError("message_id is not a uuid")

        if not isinstance(message_data, str):
            raise TypeError("message data is not a string")

        if len(message_data) < 1:
            raise ValueError("message data must not be empty")

        sender_model: uuid.UUID = self.get_user(session, sender)
        if not sender_model:
            raise ValueError('sender provided is invalid')

        message: Messages = session.exec(
            select(Messages).where(
                Messages.message_id == message_id,
                Messages.sender_id == sender_model.user_id
            )
        ).one_or_none()

        if not message:
            return DBReturnCodes.INVALID_MESSAGE

        message.message_data = message_data
        
        session.add(message)
        session.commit()

        return message.recipient


database = MainDatabase(engine)


if __name__ == "__main__":
    raise NotImplementedError("Cannot run database module as a script")
