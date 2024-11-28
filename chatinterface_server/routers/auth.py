import logging
from typing import Annotated
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket
from fastapi.security import OAuth2PasswordRequestForm

from ..models.common import AppState, SessionInfo
from ..dependencies import get_session_info

from ..internal import constants

router = APIRouter(prefix="/token", tags=['auth'])
logger: logging.Logger = logging.getLogger("chatinterface.logger.auth")


@router.post("/")
async def cookie_login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    req: Request, res: Response
) -> bool:
    if len(form_data.username) > 20:
        raise HTTPException(status_code=400, detail="Username too long")

    state: AppState = req.state
    result: str | int = await state.db.users.verify_user(form_data.username, form_data.password)

    match result:
        case 0: 
            pass
        case constants.INVALID_TOKEN | constants.NO_USER:
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        case _:
            logger.exception("Unexpected data while retrieving session token: %s", result)
            raise HTTPException(status_code=500, detail="Internal server error")

    expire_offset: timedelta = timedelta(days=30)
    expires_on: datetime = datetime.now(timezone.utc) + expire_offset

    str_date: str = datetime.strftime(expires_on, "%Y-%m-%d %H:%M:%S")
    token: str = await state.db.users.create_session(form_data.username, str_date)

    res.set_cookie(
        key="authorization", value=token,
        expires=expires_on,
        max_age=int(expire_offset.total_seconds())
    )

    return True


@router.post("/revoke")
async def revoke_token(
    session: Annotated[SessionInfo, Depends(get_session_info)],
    req: Request
) -> dict:
    state: AppState = req.state
    del_result: int | str = await state.db.users.revoke_session(session.token)

    if del_result == constants.INVALID_SESSION:
        raise HTTPException(status_code=401, detail="Session token invalid")

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
async def info_token(session: Annotated[SessionInfo, Depends(get_session_info)]) -> dict[str, str]:
    token_data: dict = {
        'username': session.username,
        'created_at': session.created_at
    }
    return token_data
