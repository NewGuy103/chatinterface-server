from fastapi.responses import RedirectResponse
from fastapi import Depends, HTTPException, Security, Cookie, WebSocket, WebSocketException
from typing import Annotated

from fastapi.security import APIKeyCookie
from sqlmodel import Session

from .internal.database import database, engine
from .models.common import UserInfo

auth_cookie = APIKeyCookie(name='x_auth_cookie', auto_error=False)


def get_session():
    with Session(engine) as session:
        yield session


async def get_session_info(
        authorization: Annotated[str, Security(auth_cookie)],
        session: 'SessionDep'
    ) -> UserInfo:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization cookie missing")

    session_expired: bool = await database.users.check_session_expired(session, authorization)
    if session_expired:
        raise HTTPException(status_code=401, detail="Session token invalid")
    
    session_info: dict[str, str | bool] = await database.users.get_session_info(session, authorization)
    return UserInfo(**session_info)


async def get_session_info_ws(
    ws: WebSocket, session: 'SessionDep',
    x_auth_cookie: Annotated[str | None, Cookie()] = None
) -> UserInfo:
    if not x_auth_cookie:
        raise WebSocketException(code=1008, reason="Authorization cookie missing")

    session_expired: bool = await database.users.check_session_expired(session, x_auth_cookie)
    if session_expired:
        raise WebSocketException(status_code=1008, reason="Session token invalid")
    
    session_info: dict[str, str | bool] = await database.users.get_session_info(session, x_auth_cookie)
    return UserInfo(**session_info)


async def login_required(session: 'SessionDep', authorization: str | None = Security(auth_cookie)) -> UserInfo | RedirectResponse:
    if not authorization:
        return RedirectResponse(url='/frontend/login', status_code=307)
    
    session_expired: bool = await database.users.check_session_expired(session, authorization)
    if session_expired:
        return RedirectResponse(url='/frontend/login', status_code=307)

    session_info: dict[str, str | bool] = await database.users.get_session_info(session, authorization)
    return UserInfo(**session_info)


HttpAuthDep = Annotated[UserInfo, Depends(get_session_info)]
AuthOrRedirectDep = Annotated[UserInfo | RedirectResponse, Depends(login_required)]

SessionDep = Annotated[Session, Depends(get_session)]
