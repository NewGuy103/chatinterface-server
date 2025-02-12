import logging
from typing import Annotated
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from ..models.common import AppState
from ..dependencies import HttpAuthDep

from ..internal import constants
from ..internal.constants import WebsocketMessages
from ..internal.config import settings

router = APIRouter(prefix="/token", tags=['auth'])
logger: logging.Logger = logging.getLogger("chatinterface_server")


@router.post("/")
async def cookie_login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    req: Request, res: Response
) -> dict:
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

    if settings.ENVIRONMENT == 'local':
        secure = False
        httponly = False
        samesite = 'none'
    else:
        secure = True
        httponly = True
        samesite = 'lax'

    res.set_cookie(
        key="authorization", value=token,
        expires=expires_on,
        max_age=int(expire_offset.total_seconds()),
        secure=secure,
        httponly=httponly,
        samesite=samesite
    )

    return {'success': True}


@router.post("/revoke_session")
async def revoke_token(
    session: HttpAuthDep,
    req: Request
) -> dict:
    state: AppState = req.state
    del_result: int | str = await state.db.users.revoke_session(session.token)

    if del_result == constants.INVALID_SESSION:
        raise HTTPException(status_code=401, detail="Session token invalid")

    await state.ws_clients.disconnect_clients_by_token(
        session.username, session.token, 
        WebsocketMessages.AUTH_REVOKED, {}
    )
    return {'success': True}


@router.get("/session_info")
async def info_token(session: HttpAuthDep) -> dict[str, str]:
    token_data: dict = {
        'username': session.username,
        'created_at': session.created_at
    }
    return token_data
