import typing
from typing import NamedTuple
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

if typing.TYPE_CHECKING:
    from ..internal.database import MainDatabase
    from ..internal.config import ConfigManager
    from ..internal.ws import WebsocketClients


class SessionInfo(BaseModel):
    username: str
    created_at: str
    expired: bool
    token: str


# used for type hints when accessing app lifespan state
class AppState(NamedTuple):
    db: 'MainDatabase'
    config: 'ConfigManager'
    ws_clients: 'WebsocketClients'
    templates: Jinja2Templates
