import logging

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, APIRouter
from fastapi.responses import RedirectResponse

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlmodel import create_engine

from .internal.config import ConfigManager, settings
from .internal.database import MainDatabase
from .internal.ws import WebsocketClients

from .models.common import AppState
from .routers import auth, chats, frontend, ws

from .version import __version__

config: ConfigManager = ConfigManager()
config.setup_logging()

logger: logging.Logger = logging.getLogger("chatinterface.logger.main")


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[AppState]:
    engine = create_engine(str(settings.SQLALCHEMY_ENGINE_URI))
    db: MainDatabase = MainDatabase(engine)

    try:
        await db.setup()
    except Exception:
        logger.exception("Database connection failed:")
        raise

    templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)
    ws_clients: WebsocketClients = WebsocketClients()

    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")
    logger.info("Application started")

    app_state: dict = {
        'ws_clients': ws_clients,
        'config': config,
        'templates': templates,
        'db': db
    }
    yield app_state

    logger.info("Application exiting")


if settings.ENVIRONMENT == 'local':
    use_debug = True
else:
    use_debug = False


app: FastAPI = FastAPI(
    lifespan=app_lifespan,
    title="chatinterface-server",
    version=__version__,
    license_info={
        'name': 'Mozilla Public License 2.0',
        'identifier': 'MPL-2.0',
        'url': 'https://www.mozilla.org/en-US/MPL/2.0/'
    },
    debug=use_debug
)

api_routers: APIRouter = APIRouter(prefix='/api')
api_routers.include_router(auth.router)

api_routers.include_router(chats.router)
api_routers.include_router(ws.router) 

app.include_router(api_routers)
app.include_router(frontend.router)


@app.get('/')
async def root_path():
    return RedirectResponse('/frontend')
