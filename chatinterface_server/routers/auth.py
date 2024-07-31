import logging
from typing import Annotated
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket
from fastapi.security import OAuth2PasswordRequestForm

from ..models import Model_SessionInfo, Model_AppState
from ..dependencies import get_session_info

router = APIRouter(prefix="/token", tags=['auth'])
logger: logging.Logger = logging.getLogger("chatinterface.logger.auth")


@router.post("/")
async def retrieve_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    req: Request
) -> dict[str, str]:
    if len(form_data.username) > 20:
        raise HTTPException(status_code=400, detail="Username too long")

    state: Model_AppState = req.state
    result: str | int = await state.db.users.verify_user(form_data.username, form_data.password)
    match result:
        case 0: 
            pass
        case "INVALID_TOKEN" | "NO_USER":
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        case _:
            logger.exception("Unexpected data while retrieving session token: %s", result)
            raise HTTPException(status_code=500, detail="Internal server error")

    # quickfix, please implement better
    expires_on: datetime = datetime.now() + timedelta(days=30)
    str_date: str = datetime.strftime(expires_on, "%Y-%m-%d %H:%M:%S")

    token: str = await state.db.users.create_session(form_data.username, str_date)
    return {'token': token}


@router.post("/revoke")
async def revoke_token(
    session: Annotated[Model_SessionInfo, Depends(get_session_info)],
    req: Request
) -> dict:
    state: Model_AppState = req.state
    del_result: int | str = await state.db.users.revoke_session(session.token)

    if del_result == "INVALID_SESSION":
        raise HTTPException(status_code=404, detail="Session token invalid")

    ws_clients_copy: dict = state.ws_clients.copy()
    for c_id, c_dict in ws_clients_copy.items():
        if not state.ws_clients.get(c_id):
            # client might disconnect right before session revoke,
            # not taking any chances and skipping that client
            continue

        token: str = c_dict['token']
        ws: WebSocket = c_dict['ws']

        if token == session.token:
            ip: str = c_dict['ip']
            logger.info("Disconnected client [%s] due to expired session token", ip)
            await ws.close(code=1008, reason="SESSION_EXPIRED")

    return {'success': True}


@router.get("/info")
async def info_token(session: Annotated[Model_SessionInfo, Depends(get_session_info)]) -> dict[str, str]:
    token_data: dict = {
        'username': session.username,
        'created_at': session.created_at
    }
    return token_data
