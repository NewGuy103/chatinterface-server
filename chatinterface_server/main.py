import os
import logging

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from .internal.config import ConfigManager
from .internal.database import MainDatabase

from .models.common import AppState
from .routers import auth, chats, ws

config: ConfigManager = ConfigManager()
config.setup_logging()

logger: logging.Logger = logging.getLogger("chatinterface.logger.main")


async def load_database() -> MainDatabase:
    db_host: str = os.getenv('CHATINTERFACE_DB_HOST', 'localhost')
    db_port: str = os.getenv('CHATINTERFACE_DB_PORT', '3306')

    db_name: str = os.getenv("CHATINTERFACE_DB_NAME", 'chatinterface_server')
    db_user: str = os.getenv("CHATINTERFACE_DB_USER", 'chatinterface_server')

    db_password: str = os.getenv("CHATINTERFACE_DB_PASSWORD", '')
    if not db_port.isdigit():
        raise ValueError("database port is not a valid port number")
    else:
        db_port: int = int(db_port)

    db: MainDatabase = MainDatabase(
        db_host, port=db_port, db_name=db_name,
        db_user=db_user, db_password=db_password
    )
    try:
        await db.setup()
    except Exception as e:
        logger.critical("Could not connect to database:", exc_info=e)
        raise

    return db


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[AppState]:
    ws_clients: dict = {}
    db: MainDatabase = await load_database()

    logger.info("Application started")
    yield AppState(db=db, ws_clients=ws_clients, config=config).model_dump()

    db.close()
    logger.info("Application exiting")


app: FastAPI = FastAPI(lifespan=app_lifespan)
app.include_router(auth.router)

app.include_router(chats.router)
app.include_router(ws.router)

