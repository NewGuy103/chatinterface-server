from pydantic import BaseModel, ConfigDict

# Imported only for the type
from starlette.websockets import WebSocket
from .internal.config import ConfigManager
from .internal.database import MainDatabase


# not used for type validation, only type hint for development
class Model_AppState(BaseModel):
    db: MainDatabase
    config: ConfigManager
    ws_clients: dict[str, 'Model_WSClientInfo']

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Model_WSClientInfo(BaseModel):
    ws: WebSocket
    ip: str
    username: str
    token: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


# type validation used in code
class Model_DBConfigFile_MySQLConfig(BaseModel):
    host: str
    port: int
    db: str
    user: str
    password: str
    pool_size: int = 10
    pool_name: str = 'chatinterface-mysql-pool'
    pool_reset_session: bool = True

    model_config = ConfigDict(extra='allow')


class Model_DBConfigFile_ExecutorConfig(BaseModel):
    max_workers: int = 10
    thread_name_prefix: str = 'mysql-databaseThread-'


class Model_DatabaseConfigFile(BaseModel):
    mysql_config: Model_DBConfigFile_MySQLConfig
    executor_config: Model_DBConfigFile_ExecutorConfig


class Model_SessionInfo(BaseModel):
    username: str
    created_at: str
    expired: bool
    token: str


class Model_WSMessageData(BaseModel):
    message: str
    data: dict


class Model_ChatWSMessageSend(BaseModel):
    recipient: str
    data: str
    id: str
