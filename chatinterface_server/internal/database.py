import asyncio
import secrets
import logging
import uuid

import argon2  # argon2-cffi

from datetime import datetime
from functools import wraps, partial
from concurrent.futures import ThreadPoolExecutor
from sqlmodel import SQLModel, Session, and_, desc, or_, select
from sqlalchemy import Engine

from . import constants
from ..models.dbtables import (
    Users, UserSessions, Messages, UserChatRelations, UserInstance
)
from ..models.chats import MessagesGetPublic

from .config import settings

logger: logging.Logger = logging.getLogger("chatinterface_server")


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
        self.__closed: bool = False
        self.engine: Engine = engine

        self.pw_hasher: argon2.PasswordHasher = argon2.PasswordHasher()
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor()

    @async_threaded
    def setup(self):
        SQLModel.metadata.create_all(self.engine)

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

    def get_userid(self, username: str) -> uuid.UUID | None:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        statement = select(Users).where(Users.username == username)
        with Session(self.engine) as session:
            result = session.exec(statement)
            user: Users | None = result.one_or_none()

        if not user:
            return None

        return user.user_id
    
    def close(self):
        if self.__closed:
            return

        self.executor.shutdown()


class UserMethods:
    def __init__(self, parent: MainDatabase) -> None:
        self.parent: MainDatabase = parent
        self.engine = parent.engine

        self.pw_hasher = parent.pw_hasher
        self.get_userid = parent.get_userid

        self.executor = parent.executor

    @async_threaded
    def add_user(self, username: str, password: str) -> str | bool:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        if not isinstance(password, str):
            raise TypeError("password is not a string")

        if len(username) > 20:
            raise ValueError("username is too long (over 20 characters)")
        
        user_id: uuid.UUID = self.get_userid(username)
        if user_id:
            return constants.USER_EXISTS

        hashed_pw: str = self.pw_hasher.hash(password)
        new_user: Users = Users(username=username, hashed_password=hashed_pw)

        with Session(self.engine) as session:
            session.add(new_user)
            session.commit()

        return True

    @async_threaded
    def delete_user(self, username: str) -> str | bool:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        if len(username) > 20:
            raise ValueError("username is too long (over 20 characters)")
        
        user_id: uuid.UUID = self.get_userid(username)
        if not user_id:
            return constants.NO_USER

        with Session(self.engine) as session:
            user: Users = session.exec(
                select(Users).where(Users.user_id == user_id)
            ).one()
            session.delete(user)
            session.commit()

        return True

    @async_threaded
    def get_users(self) -> list:
        statement = select(Users)
        with Session(self.engine) as session:
            result = session.exec(statement)
            users = result.all()

        user_list: list[str] = []
        for user in users:
            user_list.append(user.username)
        
        return user_list

    @async_threaded
    def verify_user(self, username: str, password: str) -> str | int:
        if not isinstance(username, str):
            raise TypeError("username is not a string")
        
        if not isinstance(password, str):
            raise TypeError("password is not a string")
        
        statement = select(Users).where(Users.username == username)
        with Session(self.engine) as session:
            result = session.exec(statement)
            user: Users | None = result.one_or_none()

        if not user:
            return constants.NO_USER
        
        try:
            self.pw_hasher.verify(user.hashed_password, password)
        except (argon2.exceptions.VerificationError, argon2.exceptions.VerifyMismatchError):
            return constants.INVALID_TOKEN
        
        return 0

    @async_threaded
    def create_session(self, username: str, expires_on: str) -> str:
        if not isinstance(username, str):
            raise TypeError("username is not a string")
        
        if not isinstance(expires_on, str):
            raise TypeError("expires_on is not a string")

        try:
            expiry_date: datetime = datetime.strptime(expires_on, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return constants.INVALID_DATETIME

        date_today: datetime = datetime.now()
        if date_today > expiry_date:
            return constants.DATE_EXPIRED

        user_id: uuid.UUID = self.get_userid(username)
        if not user_id:
            return constants.NO_USER

        session_token: str = secrets.token_urlsafe(32)
        new_session: UserSessions = UserSessions(
            session_id=session_token,
            user_id=user_id, 
            expires_on=expires_on
        )

        with Session(self.engine) as session:
            session.add(new_session)
            session.commit()

        return session_token

    @async_threaded
    def check_user_exists(self, username: str) -> bool:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        statement = select(Users).where(Users.username == username)
        with Session(self.engine) as session:
            result = session.exec(statement)
            user: Users = result.one_or_none()

        if user is not None:
            return True

        return False

    def get_sessions(self, username: str):
        raise NotImplementedError()

    @async_threaded
    def revoke_session(self, session_id: str) -> int | str:
        if not isinstance(session_id, str):
            raise TypeError("session ID is not a string")

        statement = select(UserSessions).where(UserSessions.session_id == session_id)
        with Session(self.engine) as session:
            result = session.exec(statement)
            user_session: UserSessions = result.one_or_none()

            if not user_session:
                return constants.INVALID_SESSION

            session.delete(user_session)
            session.commit()

        return 0

    @async_threaded
    def get_session_info(self, session_id: str) -> dict[str, str | bool] | str:
        if not isinstance(session_id, str):
            raise TypeError("session id is not a string")

        with Session(self.engine) as session:
            session_statement = select(UserSessions).where(UserSessions.session_id == session_id)

            usersession_result = session.exec(session_statement)
            user_session: UserSessions | None = usersession_result.one_or_none()

            if not user_session:
                return constants.INVALID_SESSION

            user_statement = select(Users).where(Users.user_id == user_session.user_id)
            users_result = session.exec(user_statement)

            user: Users = users_result.one()

        current_date: datetime = datetime.now()
        expired: bool = user_session.expires_on > current_date

        return {
            'created_at': datetime.strftime(user_session.created_at, "%Y-%m-%d %H:%M:%S"),
            'expired': expired,
            'username': user.username,
            'token': session_id
        }

    @async_threaded
    def check_session_validity(self, session_id: str) -> bool:
        if not isinstance(session_id, str):
            raise TypeError("session id is not a string")

        statement = select(UserSessions).where(UserSessions.session_id == session_id)
        with Session(self.engine) as session:
            result = session.exec(statement)
            user_session: UserSessions = result.one_or_none()

        if not user_session:
            return False

        expiry_date: datetime = user_session.expires_on
        current_date: datetime = datetime.now()

        expired: bool = expiry_date > current_date
        return expired


class ChatMethods:
    def __init__(self, parent: MainDatabase) -> None:
        self.parent: MainDatabase = parent
        self.engine = parent.engine

        self.executor = parent.executor
        self.get_userid = parent.get_userid

    @async_threaded
    def get_chat_relations(self, username: str) -> str | set[str]:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        sender_names: set = set()
        recipient_names: set = set()

        user_id: uuid.UUID = self.get_userid(username)
        if not user_id:
            return constants.NO_USER
        
        with Session(self.engine) as session:
            sender_statement = select(UserChatRelations).where(
                UserChatRelations.sender_id == user_id
            )
            sender_results = session.exec(sender_statement)

            recipient_statement = select(UserChatRelations).where(
                UserChatRelations.recipient_id == user_id
            )
            recipient_results = session.exec(recipient_statement)

            for relation in sender_results:
                user: Users = session.exec(
                    select(Users).where(Users.user_id == relation.recipient_id)
                ).one()
                sender_names.add(user.username)

            for relation in recipient_results:
                user: Users = session.exec(
                    select(Users).where(Users.user_id == relation.sender_id)
                ).one()
                recipient_names.add(user.username)

        return sender_names | recipient_names

    @async_threaded
    def has_chat_relation(self, sender: str, recipient: str) -> str | bool:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")
        
        if not isinstance(recipient, str):
            raise TypeError("recipient username is not a string")

        sender_id: uuid.UUID = self.get_userid(sender)
        recipient_id: uuid.UUID = self.get_userid(recipient)

        if not sender_id:
            return constants.NO_SENDER

        if not recipient_id:
            return constants.NO_RECIPIENT

        with Session(self.engine) as session:
            has_sender_relation: UserChatRelations | None = session.exec(select(UserChatRelations).where(
                UserChatRelations.sender_id == sender_id,
                UserChatRelations.recipient_id == recipient_id
            )).one_or_none()

            has_recipient_relation: UserChatRelations | None = session.exec(select(UserChatRelations).where(
                UserChatRelations.sender_id == recipient_id,
                UserChatRelations.recipient_id == sender_id
            )).one_or_none()
        
        if has_sender_relation or has_recipient_relation:
            return True
        else:
            return False

    @async_threaded
    def store_message(self, sender: str, recipient: str, message_data: str) -> uuid.UUID | str:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")
        
        if not isinstance(recipient, str):
            raise TypeError("recipient username is not a string")
        
        if not isinstance(message_data, str):
            raise TypeError("message data must be string")

        if len(message_data) < 1:
            raise ValueError("message data must not be empty")

        sender_id: uuid.UUID = self.get_userid(sender)
        recipient_id: uuid.UUID = self.get_userid(recipient)

        if not sender_id:
            return constants.NO_SENDER

        if not recipient_id:
            return constants.NO_RECIPIENT

        message_id: uuid.UUID = uuid.uuid4()
        new_message: Messages = Messages(
            message_id=message_id,
            sender_id=sender_id, 
            recipient_id=recipient_id,
            message_data=message_data
        )

        with Session(self.engine) as session:
            has_relation: UserChatRelations | None = session.exec(select(UserChatRelations).where(
                UserChatRelations.sender_id == sender_id,
                UserChatRelations.recipient_id == recipient_id
            )).one_or_none()

            if not has_relation:
                new_relation: UserChatRelations = UserChatRelations(
                    sender_id=sender_id, recipient_id=recipient_id
                )
                session.add(new_relation)

            session.add(new_message)
            session.commit()

        return message_id

    @async_threaded
    def get_messages(self, sender: str, recipient: str, amount: int = 100) -> str | list[MessagesGetPublic]:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")
        
        if not isinstance(recipient, str):
            raise TypeError("recipient username is not a string")
        
        if not isinstance(amount, int):
            raise TypeError("amount must be an int")

        sender_id: uuid.UUID = self.get_userid(sender)
        recipient_id: uuid.UUID = self.get_userid(recipient)

        if not sender_id:
            return constants.NO_SENDER

        if not recipient_id:
            return constants.NO_RECIPIENT

        with Session(self.engine) as session:
            sender_user: Users = session.exec(
                select(Users).where(Users.user_id == sender_id)
            ).one()
            recipient_user: Users = session.exec(
                select(Users).where(Users.user_id == recipient_id)
            ).one()

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
                        Messages.sender_id == sender_id, 
                        Messages.recipient_id == recipient_id
                    ),
                    and_(
                        Messages.sender_id == recipient_id,
                        Messages.recipient_id == sender_id
                    )
                )
            ).order_by(desc(Messages.send_date)).limit(amount)
            result = session.exec(statement)

            message_list: list[MessagesGetPublic] = []
            for message in result:
                if message.sender_id == sender_id:
                    sender_name: str = sender_user.username
                    recipient_name: str = recipient_user.username
                elif message.sender_id == recipient_id:
                    sender_name: str = recipient_user.username
                    recipient_name: str = sender_user.username
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
    def get_message(self, sender: str, message_id: uuid.UUID):
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")

        if not isinstance(message_id, uuid.UUID):
            raise TypeError("message_id is not a uuid")

        sender_id: uuid.UUID = self.get_userid(sender)
        if not sender_id:
            return constants.NO_SENDER

        with Session(self.engine) as session:
            sender_user: Users = session.exec(
                select(Users).where(Users.user_id == sender_id)
            ).one()

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
                    Messages.sender_id == sender_id
                )
            ).one_or_none()

            if not message:
                return constants.INVALID_MESSAGE

        return MessagesGetPublic(
            sender_name = sender_user.username,
            message_data=message.message_data,
            send_date=datetime.strftime(message.send_date, "%Y-%m-%d %H:%M:%S"),
            message_id=str(message.message_id)
        )

    @async_threaded
    def delete_message(self, sender: str, message_id: uuid.UUID) -> str | UserInstance:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")

        if not isinstance(message_id, uuid.UUID):
            raise TypeError("message_id is not a uuid")

        sender_id: uuid.UUID = self.get_userid(sender)
        if not sender_id:
            return constants.NO_SENDER

        with Session(self.engine) as session:
            message: Messages = session.exec(
                select(Messages).where(
                    Messages.message_id == message_id,
                    Messages.sender_id == sender_id
                )
            ).one_or_none()

            if not message:
                return constants.INVALID_MESSAGE

            recipient: Users = session.exec(
                select(Users).where(Users.user_id == message.recipient_id)
            ).one()
            dumped_model = recipient.model_dump()

            session.delete(message)
            session.commit()

            recipient_datamodel = UserInstance(**dumped_model)
        
        return recipient_datamodel

    @async_threaded
    def edit_message(self, sender: str, message_id: uuid.UUID, message_data: str) -> str | UserInstance:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")

        if not isinstance(message_id, uuid.UUID):
            raise TypeError("message_id is not a uuid")

        if not isinstance(message_data, str):
            raise TypeError("message data is not a string")

        if len(message_data) < 1:
            raise ValueError("message data must not be empty")

        sender_id: uuid.UUID = self.get_userid(sender)
        if not sender_id:
            return constants.NO_SENDER

        with Session(self.engine) as session:
            message: Messages = session.exec(
                select(Messages).where(
                    Messages.message_id == message_id,
                    Messages.sender_id == sender_id
                )
            ).one_or_none()

            if not message:
                return constants.INVALID_MESSAGE

            recipient: Users = session.exec(
                select(Users).where(Users.user_id == message.recipient_id)
            ).one()

            dumped_model = recipient.model_dump()
            message.message_data = message_data
            
            session.add(message)
            session.commit()

            recipient_datamodel = UserInstance(**dumped_model)

        return recipient_datamodel


if __name__ == "__main__":
    raise NotImplementedError("Cannot run database module as a script")
