import logging
from fastapi import APIRouter, HTTPException, Request

from ..dependencies import HttpAuthDep
from ..internal.config import settings
from ..internal import constants
from ..internal.constants import WebsocketMessages

from ..models.common import AppState, UsernameField
from ..models.users import AddUser

router = APIRouter(prefix="/users", tags=['users'])
logger: logging.Logger = logging.getLogger('chatinterface_server')


@router.post('/add_user')
async def add_user(
    data: AddUser,
    session: HttpAuthDep,
    req: Request
) -> dict:
    state: AppState = req.state
    # may change to roles in the future
    if session.username != settings.FIRST_USER_NAME:
        logger.warning("Unauthorized access attempted by user %s", session.username)
        raise HTTPException(status_code=401, detail="Session token invalid")

    success: str | bool = await state.db.users.add_user(data.username, data.password)
    match success:
        case True:
            pass
        case constants.USER_EXISTS:
            raise HTTPException(status_code=409, detail="User exists")
        case _:
            raise HTTPException(status_code=500, detail="Server error")

    return {'success': True}


@router.delete('/delete_user/{username}')
async def delete_user(username: UsernameField, session: HttpAuthDep, req: Request) -> dict:
    state: AppState = req.state
    # may change to roles in the future
    if session.username != settings.FIRST_USER_NAME:
        logger.warning("Unauthorized access attempted by user %s", session.username)
        raise HTTPException(status_code=401, detail="Session token invalid")

    if username == settings.FIRST_USER_NAME:
        raise HTTPException(status_code=409, detail="Cannot delete first user")

    success: str | bool = await state.db.users.delete_user(username)
    match success:
        case True:
            pass
        case constants.NO_USER:
            raise HTTPException(status_code=404, detail="User not found")
        case _:
            raise HTTPException(status_code=500, detail="Server error")

    await state.ws_clients.disconnect_all_clients(
        username, WebsocketMessages.AUTH_REVOKED,
        {}
    )
    return {'success': True}


@router.get('/retrieve_users')
async def get_users(session: HttpAuthDep, req: Request) -> list[str]:
    state: AppState = req.state
    # may change to roles in the future
    if session.username != settings.FIRST_USER_NAME:
        logger.warning("Unauthorized access attempted by user %s", session.username)
        raise HTTPException(status_code=401, detail="Session token invalid")

    user_list: list[str] = await state.db.users.get_users()
    return user_list
