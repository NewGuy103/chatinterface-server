from .models import Model_SessionInfo, Model_AppState
from fastapi import Header, Request, HTTPException
from typing import Annotated


async def get_session_info(authorization: Annotated[str, Header()], request: Request) -> Model_SessionInfo:
    state: Model_AppState = request.state
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    session_valid: bool = await state.db.users.check_session_validity(authorization)
    if not session_valid:
        raise HTTPException(status_code=401, detail="Session token invalid")
    
    session_info: dict[str, str | bool] = await state.db.users.get_session_info(authorization)
    return Model_SessionInfo(**session_info)
