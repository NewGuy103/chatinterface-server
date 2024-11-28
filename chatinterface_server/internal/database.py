import asyncio
import secrets
import logging
import uuid

import mysql.connector
import mysql.connector.cursor
import argon2  # argon2-cffi

from contextlib import contextmanager
from datetime import datetime
from functools import wraps, partial
from concurrent.futures import ThreadPoolExecutor

from . import constants

logger: logging.Logger = logging.getLogger("chatinterface.logger.database")


@contextmanager
def transaction(pool: mysql.connector.pooling.MySQLConnectionPool):
    try:
        # Type is set to a normal connection for autocomplete purposes
        conn: mysql.connector.MySQLConnection = pool.get_connection()
        logger.debug("Connection from pool acquired")
    except mysql.connector.PoolError:
        logger.exception("Could not get connection from MySQL pool:")
        raise

    try:
        cursor: mysql.connector.cursor.MySQLCursor = conn.cursor()
        cursor.execute("START TRANSACTION;")

        logger.debug("Transaction started, yielding cursor to caller")
        yield cursor

        conn.commit()
        logger.debug("Transaction committed")
    except mysql.connector.Error:
        logger.exception("MySQL transaction failed:")
        conn.rollback()

        raise
    finally:
        cursor.close()
        conn.close()

        logger.debug("Connection and cursor closed")


def async_threaded(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        partial_func: partial = partial(func, self, *args, **kwargs)

        try:
            return await loop.run_in_executor(self.executor, partial_func) 
        except Exception:
            raise
    
    return wrapper


class MainDatabase:
    def __init__(
            self, host: str, 
            port: int = 3306,
            db_name: str = 'chatinterface_server',
            db_user: str = 'chatinterface_server',
            db_password: str = '',
            pool_size: int = 10
    ) -> None:
        self.__closed: bool = False
        self.dbconfig: dict = {
            'host': host,
            'port': port,
            'db': db_name,
            'user': db_user,
            'password': db_password,
            'pool_size': pool_size,
            'pool_name': 'chatinterface_server-mysql-pool',
            'pool_reset_session': True
        }

        self.pw_hasher: argon2.PasswordHasher = argon2.PasswordHasher()
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=pool_size, 
            thread_name_prefix="chatinterface_server-mysql-thread-"
        )

    @async_threaded
    def setup(self):
        self.pool = mysql.connector.pooling.MySQLConnectionPool(**self.dbconfig)
        self.messages = ChatMethods(self)

        self.users = UserMethods(self)
        with transaction(self.pool) as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id UUID PRIMARY KEY,
                    username VARCHAR(20) NOT NULL UNIQUE,
                    
                    hashed_password VARCHAR(100) NOT NULL
                ) ENGINE = InnoDB;
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id VARCHAR(45) PRIMARY KEY,
                    user_id UUID,

                    expires_on TIMESTAMP,
                    created_at TIMESTAMP DEFAULT current_timestamp(),

                    CONSTRAINT `session-userID-exists-fk`
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                           ON DELETE CASCADE
                           ON UPDATE RESTRICT
                ) ENGINE = InnoDB;
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id UUID PRIMARY KEY,
                    sender_id UUID,

                    recipient_id UUID,
                    message_data TEXT,

                    send_date TIMESTAMP(6) NOT NULL DEFAULT current_timestamp(),
                    CONSTRAINT `message-senderID-fk`
                        FOREIGN KEY (sender_id) REFERENCES users (user_id)
                            ON DELETE CASCADE
                            ON UPDATE RESTRICT,
                    CONSTRAINT `message-recipientID-fk`
                        FOREIGN KEY (recipient_id) REFERENCES users (user_id)
                           ON DELETE CASCADE
                           ON UPDATE RESTRICT
                ) ENGINE = InnoDB;
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_send_date ON messages (send_date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_message_id ON messages (message_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users (user_id);")

    def get_userid(self, username: str) -> str:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        with transaction(self.pool) as cursor:
            cursor.execute("SELECT user_id FROM users WHERE username=%s", [username])
            user_data: tuple[str] = cursor.fetchone()

        if not user_data:
            return ''

        return user_data[0]
    
    def close(self):
        if self.__closed:
            return

        self.executor.shutdown()


class UserMethods:
    def __init__(self, parent: MainDatabase) -> None:
        self.parent: MainDatabase = parent
        self.db = parent.pool

        self.pw_hasher = parent.pw_hasher
        self.get_userid = parent.get_userid

        self.executor = parent.executor

    @async_threaded
    def add_user(self, username: str, password: str) -> str | int:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        if not isinstance(password, str):
            raise TypeError("password is not a string")

        if len(username) > 20:
            raise ValueError("username is too long (over 20 characters)")
        
        user_data: str = self.get_userid(username)
        if user_data:
            return constants.USER_EXISTS

        user_id: str = str(uuid.uuid4())
        hashed_pw: str = self.pw_hasher.hash(password)

        with transaction(self.db) as cursor:
            cursor.execute("""
                INSERT INTO users (
                    user_id, username,
                    hashed_password
                ) VALUES (%s, %s, %s)
            """, [user_id, username, hashed_pw])

        return 0

    @async_threaded
    def verify_user(self, username: str, password: str) -> str | int:
        if not isinstance(username, str):
            raise TypeError("username is not a string")
        
        if not isinstance(password, str):
            raise TypeError("password is not a string")
        
        with transaction(self.db) as cursor:
            cursor.execute("""
                SELECT hashed_password FROM users
                WHERE username=%s
            """, [username])
            user_data: tuple[str] = cursor.fetchone()

        if not user_data:
            return constants.NO_USER
        
        hashed_pw: str = user_data[0]
        try:
            self.pw_hasher.verify(hashed_pw, password)
        except (argon2.exceptions.VerificationError, argon2.exceptions.VerifyMismatchError):
            return constants.INVALID_TOKEN
        except Exception:
            logging.exception("[verify_user]: Argon2-cffi exception:")
            raise  # ideally fail
        
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

        user_id: str = self.get_userid(username)
        if not user_id:
            return constants.NO_USER

        session_token: str = secrets.token_urlsafe(32)
        with transaction(self.db) as cursor:
            cursor.execute("""
                INSERT INTO user_sessions (
                    session_id, user_id, expires_on
                ) VALUES (%s, %s, %s)
            """, [session_token, user_id, expires_on])

        return session_token

    @async_threaded
    def check_user_exists(self, username: str) -> bool:
        if not isinstance(username, str):
            raise TypeError("username is not a string")
        
        with transaction(self.db) as cursor:
            cursor.execute("SELECT username FROM users WHERE username=%s", [username])
            user: tuple[str] = cursor.fetchone()
        
        return bool(user)

    def get_sessions(self, username: str):
        raise NotImplementedError()

    @async_threaded
    def revoke_session(self, session_id: str) -> int | str:
        if not isinstance(session_id, str):
            raise TypeError("session ID is not a string")

        with transaction(self.db) as cursor:
            cursor.execute("SELECT expires_on FROM user_sessions WHERE session_id=%s", [session_id])
            session_data: tuple[str] = cursor.fetchone()

            if not session_data:
                return constants.INVALID_SESSION

            cursor.execute("""
                DELETE FROM user_sessions
                WHERE session_id=%s
            """, [session_id])
        
        return 0

    @async_threaded
    def get_session_info(self, session_id: str) -> dict[str, str | bool] | str:
        if not isinstance(session_id, str):
            raise TypeError("session id is not a string")

        with transaction(self.db) as cursor:
            cursor.execute("""
                SELECT user_id, created_at, expires_on
                FROM user_sessions
                WHERE session_id=%s
            """, [session_id])
            session_data: tuple[str] = cursor.fetchone()

            if not session_data:
                return constants.INVALID_SESSION

            user_id: str = session_data[0]
            cursor.execute("""
                SELECT username FROM users
                WHERE user_id=%s
            """, [user_id])

            username: str = cursor.fetchone()[0]
        
        created_at: str = session_data[1]
        expiry_date: str = session_data[2]

        current_date: datetime = datetime.now()
        expired: bool = expiry_date > current_date

        return {
            'created_at': datetime.strftime(created_at, "%Y-%m-%d %H:%M:%S"),
            'expired': expired,
            'username': username,
            'token': session_id
        }

    @async_threaded
    def check_session_validity(self, session_id: str) -> bool:
        if not isinstance(session_id, str):
            raise TypeError("session id is not a string")

        with transaction(self.db) as cursor:
            cursor.execute("SELECT expires_on FROM user_sessions WHERE session_id=%s", [session_id])
            session_data: tuple[str] = cursor.fetchone()
        
        if not session_data:
            return False

        expiry_date: str = session_data[0]
        current_date: datetime = datetime.now()

        expired: bool = expiry_date > current_date
        return expired


class ChatMethods:
    def __init__(self, parent: MainDatabase) -> None:
        self.parent: MainDatabase = parent
        self.db = parent.pool

        self.executor = parent.executor
        self.get_userid = parent.get_userid

    @async_threaded
    def get_previous_chats(self, username: str) -> str | set[str]:
        if not isinstance(username, str):
            raise TypeError("username is not a string")

        sender_names: set = set()
        recipient_names: set = set()

        user_id: str = self.get_userid(username)
        if not user_id:
            return constants.NO_USER
        
        with transaction(self.db) as cursor:
            cursor.execute("""
                SELECT DISTINCT recipient_id FROM messages 
                WHERE sender_id=%s
            """, [user_id])
            recipient_ids: list[tuple[str]] = cursor.fetchall()

            cursor.execute("""
                SELECT DISTINCT sender_id FROM messages 
                WHERE recipient_id=%s
            """, [user_id])
            sender_ids: list[tuple[str]] = cursor.fetchall()

            for id_tuple in recipient_ids:
                recipient_id: str = id_tuple[0]
                cursor.execute("""
                    SELECT username FROM users
                    WHERE user_id=%s
                """, [recipient_id])

                recipient_names.add(cursor.fetchone()[0])

            for id_tuple in sender_ids:
                sender_id: str = id_tuple[0]
                cursor.execute("""
                    SELECT username FROM users
                    WHERE user_id=%s
                """, [sender_id])

                sender_names.add(cursor.fetchone()[0])
        
        return sender_names | recipient_names

    @async_threaded
    def store_message(self, sender: str, recipient: str, message_data: str) -> str:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")
        
        if not isinstance(recipient, str):
            raise TypeError("recipient username is not a string")
        
        if not isinstance(message_data, str):
            raise TypeError("message data must be string")

        sender_id: str = self.get_userid(sender)
        recipient_id: str = self.get_userid(recipient)

        if not sender_id:
            return constants.NO_SENDER

        if not recipient_id:
            return constants.NO_RECIPIENT

        message_id: str = str(uuid.uuid4())
        with transaction(self.db) as cursor:
            cursor.execute("""
                INSERT INTO messages (
                    message_id, sender_id, recipient_id,
                    message_data
                ) VALUES (%s, %s, %s, %s)
            """, [message_id, sender_id, recipient_id, message_data])

        return message_id

    @async_threaded
    def get_messages(self, sender: str, recipient: str, amount: int = 100) -> str | list[tuple]:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")
        
        if not isinstance(recipient, str):
            raise TypeError("recipient username is not a string")
        
        if not isinstance(amount, int):
            raise TypeError("amount must be an int")

        sender_id: str = self.get_userid(sender)
        recipient_id: str = self.get_userid(recipient)

        if not sender_id:
            return constants.NO_SENDER

        if not recipient_id:
            return constants.NO_RECIPIENT

        with transaction(self.db) as cursor:
            cursor.execute("""
                SELECT (
                    SELECT username FROM users
                    WHERE users.user_id=messages.sender_id
                ) AS sender_name, message_data, 
                    DATE_FORMAT(send_date, "%y-%m-%d %h:%m:%S.%f"), message_id

                FROM messages WHERE (sender_id = %s AND recipient_id = %s)
                OR (sender_id = %s AND recipient_id = %s)

                ORDER BY send_date DESC;
            """, [sender_id, recipient_id, recipient_id, sender_id])
            chat_data: list[tuple] = cursor.fetchmany(amount)
            cursor.fetchall()  # discard the rest

        return chat_data

    @async_threaded
    def get_message(self, sender: str, message_id: str):
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")

        if not isinstance(message_id, str):
            raise TypeError("message_id is not a string")


        sender_id: str = self.get_userid(sender)
        if not sender_id:
            return constants.NO_SENDER

        with transaction(self.db) as cursor:
            cursor.execute("""
                SELECT (
                    SELECT username FROM users
                    WHERE users.user_id=messages.sender_id
                ) AS sender_name, message_data, DATE_FORMAT(send_date, "%y-%m-%d %h:%m:%S.%f")

                FROM messages
                WHERE message_id=%s AND sender_id=%s
            """, [message_id, sender_id])
            sender_data: tuple = cursor.fetchone()

            if not sender_data:
                return constants.INVALID_MESSAGE

        return sender_data

    @async_threaded
    def delete_message(self, sender: str, message_id: str) -> str | int:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")

        if not isinstance(message_id, str):
            raise TypeError("message_id is not a string")

        sender_id: str = self.get_userid(sender)
        if not sender_id:
            return constants.NO_SENDER

        with transaction(self.db) as cursor:
            cursor.execute("SELECT sender_id FROM messages WHERE message_id=%s", [message_id])
            sender_data: tuple[str] = cursor.fetchone()

            if not sender_data:
                return constants.INVALID_MESSAGE

            saved_sender_id: str = sender_data[0]
            if sender_id != saved_sender_id:
                return constants.ID_MISMATCH
            
            cursor.execute("""
                DELETE FROM messages
                WHERE message_id=%s
            """, [message_id])
        
        return 0

    @async_threaded
    def edit_message(self, sender: str, message_id: str, message_data: str) -> str | int:
        if not isinstance(sender, str):
            raise TypeError("sender username is not a string")

        if not isinstance(message_id, str):
            raise TypeError("message_id is not a string")

        if not isinstance(message_data, str):
            raise TypeError("message data is not a string")

        if len(message_data) < 1:
            raise ValueError("message data must not be empty")

        sender_id: str = self.get_userid(sender)
        if not sender_id:
            return constants.NO_SENDER

        with transaction(self.db) as cursor:
            cursor.execute("SELECT sender_id FROM messages WHERE message_id=%s", [message_id])
            sender_data: tuple[str] = cursor.fetchone()

            if not sender_data:
                return constants.INVALID_MESSAGE

            saved_sender_id: str = sender_data[0]
            if sender_id != saved_sender_id:
                return constants.ID_MISMATCH

            cursor.execute("""
                UPDATE messages
                SET message_data=%s
                WHERE message_id=%s
            """, [message_data, message_id])
        
        return 0


if __name__ == "__main__":
    raise NotImplementedError("Cannot run database module as a script")
