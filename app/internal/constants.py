from enum import StrEnum


class DBReturnCodes(StrEnum):
    USER_EXISTS = "USER_EXISTS"
    NO_USER = "NO_USER"

    INVALID_TOKEN = "INVALID_TOKEN"
    INVALID_SESSION = "INVALID_SESSION"

    NO_RECIPIENT = "NO_RECIPIENT"
    INVALID_MESSAGE = "INVALID_MESSAGE"


class WebsocketMessages(StrEnum):
    MESSAGE_RECEIVED = 'message.received'
    MESSAGE_UPDATE = 'message.update'
    MESSAGE_DELETE = 'message.delete'
    MESSAGE_COMPOSE = 'message.compose'
    AUTH_REVOKED = 'auth.revoked'
