import logging
from typing import Annotated
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestFormStrict

from ..models.common import AppState
from ..dependencies import HttpAuthDep, SessionDep

from ..internal.database import database
from ..internal.constants import WebsocketMessages, DBReturnCodes
from ..internal.config import settings

router = APIRouter(prefix="/token", tags=['auth'])
logger: logging.Logger = logging.getLogger("chatinterface_server")


@router.post("/")
async def cookie_login(
    form_data: Annotated[OAuth2PasswordRequestFormStrict, Depends()], 
    res: Response,
    session: SessionDep
) -> dict:
    if len(form_data.username) > 20:
        raise HTTPException(status_code=400, detail="Username too long")

    result: str | int = await database.users.verify_user(session, form_data.username, form_data.password)
    match result:
        case 0: 
            pass
        case DBReturnCodes.INVALID_TOKEN | DBReturnCodes.NO_USER:
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        case _:
            logger.exception("Unexpected data while retrieving session token: %s", result)
            raise HTTPException(status_code=500, detail="Internal server error")

    expire_offset: timedelta = timedelta(days=30)
    expires_on: datetime = datetime.now(timezone.utc) + expire_offset

    str_date: str = datetime.strftime(expires_on, "%Y-%m-%d %H:%M:%S")
    token: str = await database.users.create_session(session, form_data.username, str_date)

    if settings.ENVIRONMENT == 'local':
        secure = False
        httponly = False
        # samesite is 'lax' and not 'none' due to secure attribute not being set
        samesite = 'lax'
    else:
        secure = True
        httponly = True
        samesite = 'lax'

    res.set_cookie(
        key="x_auth_cookie",
        value=token,
        expires=expires_on,
        max_age=int(expire_offset.total_seconds()),
        secure=secure,
        httponly=httponly,
        samesite=samesite
    )

    return {'success': True}


@router.post("/revoke")
async def revoke_token(
    user: HttpAuthDep,
    req: Request
) -> dict:
    """Revokes the current cookie passed."""
    state: AppState = req.state

    await database.users.revoke_session(user.token)
    await state.ws_clients.disconnect_clients_by_token(
        user.username, user.token, 
        WebsocketMessages.AUTH_REVOKED, {}
    )
    
    return {'success': True}


@router.get("/info")
async def info_token(user: HttpAuthDep) -> dict[str, str]:
    token_data: dict = {
        'username': user.username,
        'created_at': user.created_at
    }
    return token_data
