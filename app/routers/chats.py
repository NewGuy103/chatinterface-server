import logging
import uuid

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import NonNegativeInt, PositiveInt

from ..models.dbtables import Users
from ..models.common import AppState
from ..models.chats import ComposeMessage, EditMessage, SendMessage, MessagesGetPublic
from ..models.ws import MessageDelete, MessageUpdate

from ..dependencies import HttpAuthDep, SessionDep
from ..internal.database import database
from ..internal.constants import WebsocketMessages, DBReturnCodes

router = APIRouter(prefix="/chats", tags=['chats'])
logger: logging.Logger = logging.getLogger("chatinterface_server")


@router.get("/recipients")
async def get_chat_relations(user: HttpAuthDep, session: SessionDep) -> set[str]:
    recipients: set[str] = await database.messages.get_chat_relations(session, user.username)
    return recipients


@router.get("/messages")
async def get_previous_messages(
    user: HttpAuthDep, session: SessionDep,
    recipient: Annotated[str, Query(description="Recipient username", max_length=20, strict=True)],

    amount: PositiveInt = Query(100, description="Amount of messages to fetch (fetches latest messages)"),
    offset: NonNegativeInt = Query(0, description="Offset of messages starting from latest")
) -> list[MessagesGetPublic]:
    result: list[MessagesGetPublic] | str = await database.messages.get_messages(
        session, user.username,
        recipient, amount=amount, 
        offset=offset
    )
    match result:
        case list():
            pass
        case DBReturnCodes.NO_RECIPIENT:
            raise HTTPException(status_code=404, detail="User not found")
        case _:
            logger.error("Unexpected data while fetching messages: %s", result)
            raise HTTPException(status_code=500, detail="Server error")

    return result


@router.get('/user_exists')
async def check_user_exists(
    username: Annotated[str, Query(description="Username to check", max_length=20, strict=True)],
    user: HttpAuthDep, session: SessionDep
) -> bool:
    user_exists: bool = await database.users.check_user_exists(session, username)
    return user_exists


@router.post('/message')
async def send_message(
    data: SendMessage, req: Request,
    user: HttpAuthDep, session: SessionDep
) -> uuid.UUID:
    state: AppState = req.state
    if data.recipient == user.username:
        raise HTTPException(status_code=400, detail="Cannot send message to self")

    has_relation: bool | str = await database.messages.has_chat_relation(session, user.username, data.recipient)

    match has_relation:
        case True:
            pass
        case False:
            raise HTTPException(status_code=409, detail="Cannot compose message from send_message")
        case DBReturnCodes.NO_RECIPIENT:
            raise HTTPException(status_code=404, detail="Recipient not found")
        case _:
            logger.error("Unexpected data when checking chat relation: %s", has_relation)
            raise HTTPException(status_code=500, detail="Server error")

    message_id: uuid.UUID = await database.messages.store_message(
        session, user.username, 
        data.recipient, data.message_data
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
        sender_name=user.username,
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
        user.username, WebsocketMessages.MESSAGE_RECEIVED,
        dumped_model
    )
    return message_id


@router.post('/message/compose')
async def compose_new_message(
    data: ComposeMessage, req: Request, 
    user: HttpAuthDep, session: SessionDep
) -> uuid.UUID:
    state: AppState = req.state
    if data.recipient == user.username:
        raise HTTPException(status_code=400, detail="Cannot send message to self")

    has_relation: bool | str = await database.messages.has_chat_relation(session, user.username, data.recipient)
    # has_relation = False
    match has_relation:
        case False:
            pass
        case True:
            raise HTTPException(status_code=409, detail="Existing conversation exists")
        case DBReturnCodes.NO_RECIPIENT:
            raise HTTPException(status_code=404, detail="Recipient not found")
        case _:
            logger.error("Unexpected data when checking chat relation: %s", has_relation)
            raise HTTPException(status_code=500, detail="Server error")

    message_id: uuid.UUID = await database.messages.store_message(
        session, user.username, 
        data.recipient, data.message_data
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
        sender_name=user.username,
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
        user.username, WebsocketMessages.MESSAGE_COMPOSE,
        dumped_model
    )
    return message_id



@router.get('/message/{message_id}')
async def get_message(message_id: uuid.UUID, user: HttpAuthDep, session: SessionDep) -> MessagesGetPublic:
    message_data: str | MessagesGetPublic = await database.messages.get_message(session, user.username, message_id)

    match message_data:
        case MessagesGetPublic():
            pass
        case DBReturnCodes.INVALID_MESSAGE:
            raise HTTPException(status_code=404, detail="Invalid message ID provided")
        case _: 
            logger.error(
                "Fetching message ID [%s] failed due to unexpected result: %s", 
                message_id, message_data
            )
            raise HTTPException(status_code=500, detail="Server error")
    
    return message_data


@router.delete('/message/{message_id}')
async def delete_message(
    message_id: uuid.UUID, req: Request,
    user: HttpAuthDep, session: SessionDep
) -> dict:
    state: AppState = req.state
    recipient: str | Users = await database.messages.delete_message(session, user.username, message_id)

    match recipient:
        case Users():
            pass
        case DBReturnCodes.INVALID_MESSAGE:
            raise HTTPException(status_code=404, detail="Invalid message ID or not message owner")
        case _: 
            logger.error(
                "Deleting message ID [%s] failed due to unexpected result: %s", 
                message_id, recipient
            )
            raise HTTPException(status_code=500, detail="Server error")

    model_payload: MessageDelete = MessageDelete(
        sender_name=user.username,
        recipient_name=recipient.username,
        message_id=str(message_id)
    )
    dumped_model = model_payload.model_dump(mode='json')

    await state.ws_clients.broadcast_message(
        recipient.username, WebsocketMessages.MESSAGE_DELETE,
        dumped_model
    )
    await state.ws_clients.broadcast_message(
        user.username, WebsocketMessages.MESSAGE_DELETE,
        dumped_model
    )
    return {'success': True}


@router.patch('/message/{message_id}')
async def edit_message(
    message_id: uuid.UUID, data: EditMessage,
    req: Request, user: HttpAuthDep,
    session: SessionDep
) -> dict:
    state: AppState = req.state
    recipient: str | Users = await database.messages.edit_message(
        session, user.username, 
        message_id, data.message_data
    )

    match recipient:
        case Users():
            pass
        case DBReturnCodes.INVALID_MESSAGE:
            raise HTTPException(status_code=404, detail="Invalid message ID provided")
        case _: 
            logger.error("Editing message ID [%s] failed due to unexpected result: %s", message_id, recipient)
            raise HTTPException(status_code=500, detail="Server error")

    # seems too much for just one item but this is to make it easier to expand next time
    model_payload: MessageUpdate = MessageUpdate(
        message_data=data.message_data,
        sender_name=user.username,
        recipient_name=recipient.username,
        message_id=str(message_id)
    )
    dumped_model = model_payload.model_dump(mode='json')

    await state.ws_clients.broadcast_message(
        recipient.username, WebsocketMessages.MESSAGE_UPDATE,
        dumped_model
    )
    await state.ws_clients.broadcast_message(
        user.username, WebsocketMessages.MESSAGE_UPDATE,
        dumped_model
    )
    return {'success': True}
