import os
import logging

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, APIRouter
from fastapi.responses import RedirectResponse

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .internal.config import ConfigManager
from .internal.database import MainDatabase

from .models.common import AppState
from .routers import auth, chats, frontend, ws

from .version import __version__

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
    templates = Jinja2Templates(directory=templates_directory)
    ws_clients: dict = {}

    db: MainDatabase = await load_database()
    logger.info("Application started")

    app_state: dict = {
        'db': db, 
        'ws_clients': ws_clients,
        'config': config, 
        'templates': templates
    }
    yield app_state

    db.close()
    logger.info("Application exiting")


static_files_directory: str = os.getenv("CHATINTERFACE_STATIC_DIR", "./static")
templates_directory: str = os.getenv("CHATINTERFACE_TEMPLATES_DIR", "./templates")

app: FastAPI = FastAPI(
    lifespan=app_lifespan,
    title="chatinterface-server",
    version=__version__,
    license_info={
        'name': 'GNU General Public License Version 2.0, June 1991',
        'identifier': 'GPL-2.0',
        'url': 'http://www.gnu.org/licenses/gpl-2.0.txt'
    }
)

app.mount("/static", StaticFiles(directory=static_files_directory), name="static")

api_routers: APIRouter = APIRouter(prefix='/api')
api_routers.include_router(auth.router)

api_routers.include_router(chats.router)
api_routers.include_router(ws.router) 

app.include_router(api_routers)
app.include_router(frontend.router)


@app.get('/')
async def root_path():
    return RedirectResponse('/frontend')
