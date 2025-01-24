from datetime import datetime
import logging

from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request, Query, WebSocket

from ..models.common import AppState
from ..models.chats import ComposeMessage, EditMessage, SendMessage
from ..dependencies import HttpAuthDep
from ..internal import constants

router = APIRouter(prefix="/chats", tags=['chats'])
logger: logging.Logger = logging.getLogger("chatinterface.logger.ws")


@router.get("/recipients")
async def get_previous_chats(
    session: HttpAuthDep,
    req: Request
) -> set[str]:
    state: AppState = req.state
    recipients: set[str] = await state.db.messages.get_previous_chats(session.username)
    return recipients


@router.get("/messages")
async def get_previous_messages(
    req: Request,
    session: HttpAuthDep,
    recipient: Annotated[str, Query(description="Recipient username", max_length=20, strict=True)],

    amount: int = Query(100, description="Amount of messages to fetch (fetches latest messages)")
) -> list[tuple[str, bytes, str, str]]:
    state: AppState = req.state
    result: list[tuple] | str = await state.db.messages.get_messages(
        session.username, recipient, amount
    )
    match result:
        case list():
            pass
        case constants.NO_RECIPIENT:
            raise HTTPException(status_code=404, detail="User not found")
        case _:
            logger.error("Unexpected data while fetching messages: %s", result)
            raise HTTPException(status_code=500, detail="Server error")

    return result


@router.get('/user_exists')
async def check_user_exists(
    req: Request,
    username: Annotated[str, Query(description="Username to check", max_length=20, strict=True)],
    session: HttpAuthDep
) -> bool:
    state: AppState = req.state
    user_exists: bool = await state.db.users.check_user_exists(username)
    return user_exists


@router.post('/send_message')
async def send_message(
    data: SendMessage,
    req: Request,
    session: HttpAuthDep
) -> str:
    state: AppState = req.state
    has_message: list | str = await state.db.messages.get_messages(
        session.username, data.recipient,
        amount=1
    )

    match has_message:
        case list() if has_message:
            pass
        case list() if not has_message:
            raise HTTPException(status_code=409, detail="Cannot compose message from send_message")
        case constants.NO_RECIPIENT:
            raise HTTPException(status_code=404, detail="Recipient not found")
        case _:
            logger.error("Unexpected data when checking if has_message: %s", has_message)
            raise HTTPException(status_code=500, detail="Server error")

    store_result: str = await state.db.messages.store_message(
        session.username, data.recipient,
        data.message_data
    )
    try:
        UUID(store_result, version=4)
    except ValueError:
        logger.exception("send_message did not return a UUID, returned '%s'", store_result)
        raise HTTPException(status_code=500, detail="Server error") from None

    # Note: Make a class or dependency class to do this, it looks bad to couple this
    # together, but it's a temp fix
    current_time: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    recipient_payload: dict = {
        'sender': session.username,
        'data': data.message_data,
        'timestamp': current_time,
        'message_id': store_result
    }

    message_data: bytes = {
        'message': 'message.received',
        'data': recipient_payload
    }

    for client_info in state.ws_clients.values():
        if client_info.username != data.recipient:
            continue

        recipient_ws: WebSocket = client_info.ws
        await recipient_ws.send_json(message_data)

    return store_result


@router.post('/compose_message')
async def compose_new_message(
    data: ComposeMessage,
    req: Request,
    session: HttpAuthDep
):
    state: AppState = req.state
    if data.recipient == session.username:
        raise HTTPException(status_code=400, detail="Cannot send message to self")

    has_message: list | str = await state.db.messages.get_messages(session.username, data.recipient, amount=1)
    match has_message:
        case list() if has_message:
            raise HTTPException(status_code=409, detail="Existing conversation exists")
        case constants.NO_RECIPIENT:
            raise HTTPException(status_code=404, detail="User not found")

    result: str | int = await state.db.messages.store_message(
        session.username, data.recipient, data.message_data
    )
    match result:
        case str():
            pass
        case _:
            logger.error("Unexpected data while fetching messages: %s", result)
            raise HTTPException(status_code=500, detail="Server error")

    return result



@router.get('/get_message/{message_id}')
async def get_message(
    message_id: str, 
    req: Request, 
    session: HttpAuthDep
):
    state: AppState = req.state
    message_data: str | tuple = await state.db.messages.get_message(session.username, message_id)

    match message_data:
        case tuple():
            pass
        case constants.INVALID_MESSAGE:
            raise HTTPException(status_code=404, detail="Invalid message ID provided")
        case _: 
            logger.error("Unexpected data while fetching messages: %s", message_data)
            raise HTTPException(status_code=500, detail="Server error")
    
    return message_data


@router.delete('/delete_message/{message_id}')
async def delete_message(
    message_id: str,
    req: Request,
    session: HttpAuthDep
) -> int:
    state: AppState = req.state
    delete_result: str | int = await state.db.messages.delete_message(session.username, message_id)

    match delete_result:
        case 0:
            pass
        case constants.INVALID_MESSAGE | constants.ID_MISMATCH:
            raise HTTPException(status_code=404, detail="Invalid message ID provided")
        case _: 
            logger.error("Unexpected data while fetching messages: %s", delete_result)
            raise HTTPException(status_code=500, detail="Server error")
    
    return delete_result


@router.patch('/edit_message/{message_id}')
async def edit_message(
    message_id: str,
    message_data: EditMessage,
    req: Request,
    session: HttpAuthDep
) -> int:
    state: AppState = req.state
    edit_result: str | int = await state.db.messages.edit_message(
        session.username, message_id,
        message_data.message_data
    )

    match edit_result:
        case 0:
            pass
        case constants.INVALID_MESSAGE | constants.ID_MISMATCH:
            raise HTTPException(status_code=404, detail="Invalid message ID provided")
        case _: 
            logger.error("Editing message ID [%s] failed due to unexpected result: %s", message_id, edit_result)
            raise HTTPException(status_code=500, detail="Server error")

    return edit_result
