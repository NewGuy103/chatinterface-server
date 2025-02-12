import typing
from typing import Annotated, NamedTuple
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

if typing.TYPE_CHECKING:
    from ..internal.database import MainDatabase
    from ..internal.config import ConfigManager
    from ..internal.ws import WebsocketClients


UsernameField = Annotated[str, Field(max_length=20, min_length=1)]

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
