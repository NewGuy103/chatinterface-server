import logging
import uuid

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Query

from ..models.dbtables import UserInstance
from ..models.common import AppState
from ..models.chats import ComposeMessage, EditMessage, SendMessage, MessagesGetPublic
from ..models.ws import MessageDelete, MessageUpdate

from ..dependencies import HttpAuthDep
from ..internal import constants
from ..internal.constants import WebsocketMessages

router = APIRouter(prefix="/chats", tags=['chats'])
logger: logging.Logger = logging.getLogger("chatinterface.logger.ws")


@router.get("/retrieve_recipients")
async def get_chat_relations(
    session: HttpAuthDep,
    req: Request
) -> set[str]:
    state: AppState = req.state
    recipients: set[str] = await state.db.messages.get_chat_relations(session.username)
    return recipients


@router.get("/retrieve_messages")
async def get_previous_messages(
    req: Request,
    session: HttpAuthDep,
    recipient: Annotated[str, Query(description="Recipient username", max_length=20, strict=True)],

    amount: int = Query(100, description="Amount of messages to fetch (fetches latest messages)")
) -> list[MessagesGetPublic]:   
    state: AppState = req.state
    result: list[MessagesGetPublic] | str = await state.db.messages.get_messages(
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
) -> uuid.UUID:
    state: AppState = req.state
    if data.recipient == session.username:
        raise HTTPException(status_code=400, detail="Cannot send message to self")

    has_relation: bool | str = await state.db.messages.has_chat_relation(session.username, data.recipient)

    match has_relation:
        case True:
            pass
        case False:
            raise HTTPException(status_code=409, detail="Cannot compose message from send_message")
        case constants.NO_RECIPIENT:
            raise HTTPException(status_code=404, detail="Recipient not found")
        case _:
            logger.error("Unexpected data when checking chat relation: %s", has_relation)
            raise HTTPException(status_code=500, detail="Server error")

    message_id: uuid.UUID = await state.db.messages.store_message(
        session.username, data.recipient,
        data.message_data
    )

    match message_id:
        case uuid.UUID():
            pass
        case _:
            logger.error("Unexpected data when sending message: %s", message_id)
            raise HTTPException(status_code=500, detail="Server error")

    current_time: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

    # Using a model instead of a dict so its easy to update
    recipient_payload: MessagesGetPublic = MessagesGetPublic(
        sender_name=session.username,
        recipient_name=data.recipient,
        message_data=data.message_data,
        send_date=current_time,
        message_id=message_id
    )

    dumped_model = recipient_payload.model_dump(mode='json')
    await state.ws_clients.broadcast_message(
        data.recipient, WebsocketMessages.MESSAGE_RECEIVED,
        dumped_model
    )

    await state.ws_clients.broadcast_message(
        session.username, WebsocketMessages.MESSAGE_RECEIVED,
        dumped_model
    )
    return message_id


@router.post('/compose_message')
async def compose_new_message(
    data: ComposeMessage,
    req: Request,
    session: HttpAuthDep
) -> uuid.UUID:
    state: AppState = req.state
    if data.recipient == session.username:
        raise HTTPException(status_code=400, detail="Cannot send message to self")

    has_relation: bool | str = await state.db.messages.has_chat_relation(session.username, data.recipient)

    match has_relation:
        case False:
            pass
        case True:
            raise HTTPException(status_code=409, detail="Existing conversation exists")
        case constants.NO_RECIPIENT:
            raise HTTPException(status_code=404, detail="Recipient not found")
        case _:
            logger.error("Unexpected data when checking chat relation: %s", has_relation)
            raise HTTPException(status_code=500, detail="Server error")

    message_id: uuid.UUID = await state.db.messages.store_message(
        session.username, data.recipient, data.message_data
    )
    match message_id:
        case uuid.UUID():
            pass
        case _:
            logger.error("Unexpected data while composing message: %s", message_id)
            raise HTTPException(status_code=500, detail="Server error")

    current_time: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

    # Using a model instead of a dict so its easy to update
    recipient_payload: MessagesGetPublic = MessagesGetPublic(
        sender_name=session.username,
        recipient_name=data.recipient,
        message_data=data.message_data,
        send_date=current_time,
        message_id=message_id
    )

    dumped_model = recipient_payload.model_dump(mode='json')
    await state.ws_clients.broadcast_message(
        data.recipient, WebsocketMessages.MESSAGE_COMPOSE,
        dumped_model
    )

    await state.ws_clients.broadcast_message(
        session.username, WebsocketMessages.MESSAGE_COMPOSE,
        dumped_model
    )
    return message_id



@router.get('/get_message/{message_id}')
async def get_message(
    message_id: uuid.UUID, 
    req: Request, 
    session: HttpAuthDep
) -> MessagesGetPublic:
    state: AppState = req.state
    message_data: str | MessagesGetPublic = await state.db.messages.get_message(session.username, message_id)

    match message_data:
        case MessagesGetPublic():
            pass
        case constants.INVALID_MESSAGE:
            raise HTTPException(status_code=404, detail="Invalid message ID provided")
        case _: 
            logger.error(
                "Fetching message ID [%s] failed due to unexpected result: %s", 
                message_id, message_data
            )
            raise HTTPException(status_code=500, detail="Server error")
    
    return message_data


@router.delete('/delete_message/{message_id}')
async def delete_message(
    message_id: uuid.UUID,
    req: Request,
    session: HttpAuthDep
) -> dict:
    state: AppState = req.state
    recipient: str | UserInstance = await state.db.messages.delete_message(session.username, message_id)

    match recipient:
        case UserInstance():
            pass
        case constants.INVALID_MESSAGE:
            raise HTTPException(status_code=404, detail="Invalid message ID or not message owner")
        case _: 
            logger.error(
                "Deleting message ID [%s] failed due to unexpected result: %s", 
                message_id, recipient
            )
            raise HTTPException(status_code=500, detail="Server error")

    model_payload: MessageDelete = MessageDelete(
        sender_name=session.username,
        recipient_name=recipient.username,
        message_id=str(message_id)
    )
    dumped_model = model_payload.model_dump(mode='json')

    await state.ws_clients.broadcast_message(
        recipient.username, WebsocketMessages.MESSAGE_DELETE,
        dumped_model
    )
    await state.ws_clients.broadcast_message(
        session.username, WebsocketMessages.MESSAGE_DELETE,
        dumped_model
    )
    return {'success': True}


@router.patch('/edit_message/{message_id}')
async def edit_message(
    message_id: uuid.UUID,
    data: EditMessage,
    req: Request,
    session: HttpAuthDep
) -> dict:
    state: AppState = req.state
    recipient: str | UserInstance = await state.db.messages.edit_message(
        session.username, message_id,
        data.message_data
    )

    match recipient:
        case UserInstance():
            pass
        case constants.INVALID_MESSAGE:
            raise HTTPException(status_code=404, detail="Invalid message ID provided")
        case _: 
            logger.error("Editing message ID [%s] failed due to unexpected result: %s", message_id, recipient)
            raise HTTPException(status_code=500, detail="Server error")

    # seems too much for just one item but this is to make it easier to expand next time
    model_payload: MessageUpdate = MessageUpdate(
        message_data=data.message_data,
        sender_name=session.username,
        recipient_name=recipient.username,
        message_id=str(message_id)
    )
    dumped_model = model_payload.model_dump(mode='json')

    await state.ws_clients.broadcast_message(
        recipient.username, WebsocketMessages.MESSAGE_UPDATE,
        dumped_model
    )
    await state.ws_clients.broadcast_message(
        session.username, WebsocketMessages.MESSAGE_UPDATE,
        dumped_model
    )
    return {'success': True}
