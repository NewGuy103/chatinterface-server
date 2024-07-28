from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from pydantic import ValidationError
from .internal.config import ConfigManager
from .internal.database import MainDatabase

from .models import Model_AppState, Model_DatabaseConfigFile
from .routers import auth, chats, ws

config: ConfigManager = ConfigManager()
config.setup_logging()


async def load_database(db_config: Model_DatabaseConfigFile) -> MainDatabase:
    mysql_conf: dict = db_config.mysql_config.model_dump()
    executor_conf: dict = db_config.executor_config.model_dump()

    db: MainDatabase = MainDatabase(mysql_conf, executor_conf)
    await db.setup()

    return db


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[Model_AppState]:
    ws_clients: dict = {}
    db_config: dict = config.get_database_config()

    try:
        valid_db_conf: Model_DatabaseConfigFile = Model_DatabaseConfigFile(**db_config)
    except ValidationError:
        raise RuntimeError("database configuration file invalid!") from None

    db: MainDatabase = await load_database(valid_db_conf)

    yield Model_AppState(db=db, ws_clients=ws_clients, config=config)
    db.close()


app: FastAPI = FastAPI(lifespan=app_lifespan)
app.include_router(auth.router)

app.include_router(chats.router)
app.include_router(ws.router)
