import logging
from fastapi import APIRouter, HTTPException, Request

from ..dependencies import HttpAuthDep, SessionDep
from ..internal.config import settings
from ..internal.database import database
from ..internal.constants import WebsocketMessages, DBReturnCodes

from ..models.common import AppState, UsernameField
from ..models.users import AddUser

router = APIRouter(prefix="/users", tags=['users'])
logger: logging.Logger = logging.getLogger('chatinterface_server')


@router.post('/')
async def add_user(
    data: AddUser, user: HttpAuthDep,
    session: SessionDep
) -> dict:
    if user.username != settings.FIRST_USER_NAME:
        logger.warning("Unauthorized access attempted by user %s", user.username)
        raise HTTPException(status_code=401, detail="Session token invalid")

    success: str | bool = await database.users.add_user(session, data.username, data.password)
    match success:
        case True:
            pass
        case DBReturnCodes.USER_EXISTS:
            raise HTTPException(status_code=409, detail="User exists")
        case _:
            raise HTTPException(status_code=500, detail="Server error")

    return {'success': True}


@router.delete('/{username}')
async def delete_user(username: UsernameField, user: HttpAuthDep, req: Request, session: SessionDep) -> dict:
    state: AppState = req.state
    # may change to roles in the future
    if user.username != settings.FIRST_USER_NAME:
        logger.warning("Unauthorized access attempted by user %s", user.username)
        raise HTTPException(status_code=401, detail="Session token invalid")

    if username == settings.FIRST_USER_NAME:
        raise HTTPException(status_code=409, detail="Cannot delete first user")

    success: str | bool = await database.users.delete_user(session, username)
    match success:
        case True:
            pass
        case DBReturnCodes.NO_USER:
            raise HTTPException(status_code=404, detail="User not found")
        case _:
            raise HTTPException(status_code=500, detail="Server error")

    await state.ws_clients.disconnect_all_clients(
        username, WebsocketMessages.AUTH_REVOKED,
        {}
    )
    return {'success': True}


@router.get('/')
async def get_users(user: HttpAuthDep, session: SessionDep) -> list[str]:
    if user.username != settings.FIRST_USER_NAME:
        logger.warning("Unauthorized access attempted by user %s", user.username)
        raise HTTPException(status_code=401, detail="Session token invalid")

    user_list: list[str] = await database.users.get_users(session)
    return user_list
