from pydantic import BaseModel, ConfigDict

from ..internal.database import MainDatabase
from ..internal.config import ConfigManager

from .ws import ClientInfo

class SessionInfo(BaseModel):
    username: str
    created_at: str
    expired: bool
    token: str

# not used for type validation, only type hint for development
class AppState(BaseModel):
    db: MainDatabase
    config: ConfigManager
    ws_clients: dict[str, 'ClientInfo']

    model_config = ConfigDict(arbitrary_types_allowed=True)