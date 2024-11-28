from fastapi.responses import RedirectResponse
from .models.common import SessionInfo, AppState
from fastapi import Cookie, Request, HTTPException, WebSocket
from typing import Annotated


async def get_session_info(authorization: Annotated[str, Cookie()], request: Request) -> SessionInfo:
    state: AppState = request.state
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization cookie missing")

    session_valid: bool = await state.db.users.check_session_validity(authorization)
    if not session_valid:
        raise HTTPException(status_code=401, detail="Session token invalid")
    
    session_info: dict[str, str | bool] = await state.db.users.get_session_info(authorization)
    return SessionInfo(**session_info)


async def get_session_info_ws(authorization: Annotated[str, Cookie()], ws: WebSocket) -> SessionInfo:
    state: AppState = ws.state
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization cookie missing")

    session_valid: bool = await state.db.users.check_session_validity(authorization)
    if not session_valid:
        raise HTTPException(status_code=401, detail="Session token invalid")
    
    session_info: dict[str, str | bool] = await state.db.users.get_session_info(authorization)
    return SessionInfo(**session_info)


async def login_required(
    request: Request,
    authorization: str | None = Cookie(None),
) -> SessionInfo | RedirectResponse:
    state: AppState = request.state
    if not authorization:
        return RedirectResponse(url='/frontend/login', status_code=307)
    
    session_valid: bool = await state.db.users.check_session_validity(authorization)
    if not session_valid:
        return RedirectResponse(url='/frontend/login', status_code=307)

    session_info: dict[str, str | bool] = await state.db.users.get_session_info(authorization)
    return SessionInfo(**session_info)
