import asyncio
import json
from typing import Annotated
import uuid
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from pydantic import ValidationError

from ..models.common import SessionInfo, AppState
from ..models.ws import ClientInfo, MessageData

from ..dependencies import get_session_info_ws

router: APIRouter = APIRouter(prefix="/ws", tags=['websocket'])
logger: logging.Logger = logging.getLogger("chatinterface.logger.ws")


@router.websocket("/chat")
async def create_websocket(websocket: WebSocket, session: Annotated[SessionInfo, Depends(get_session_info_ws)]):
    state: AppState = websocket.state
    await websocket.accept()

    client_id: str = str(uuid.uuid4())
    client_info_dict: dict[str, WebSocket | str] = {
        'ws': websocket,
        'ip': f"{websocket.client.host}:{websocket.client.port}",
        'username': session.username,
        'token': session.token
    }

    client_info: ClientInfo = ClientInfo(**client_info_dict)
    state.ws_clients[client_id] = client_info

    await websocket.send_json("OK")
    try:
        ws_authorized_logmsg: str = "WebSocket by user '%s' from IP '%s' authorized"
        logger.debug(ws_authorized_logmsg, client_info.username, client_info.ip)

        while True:
            try:
                ws_message: dict = await asyncio.wait_for(websocket.receive_json(), timeout=20)
            except json.JSONDecodeError:
                await websocket.close(code=1003, reason="INVALID_JSON")
                return

            if not isinstance(ws_message, dict):
                await websocket.close(code=1003, reason="INVALID_MSGPACK")
                return

            try:
                loaded_msg: MessageData = MessageData(**ws_message)  # noqa | disabled ws sending
            except ValidationError:
                await websocket.close(code=1008, reason="INVALID_DATA")
                return

            if loaded_msg.message == 'keepalive':
                await websocket.send_json({
                    'message': 'ALIVE',
                    'data': {}
                })
                continue

            await websocket.close(code=1008, reason="SEND_UNSUPPORTED")
    except WebSocketDisconnect as e:
        code: int = e.code

        reason: str | None = e.reason or None
        logmsg: str = "User '%s' from IP '%s' disconnected with code [%d] and reason [%s]"

        debug_logmsg: str = "WebSocketDisconnect traceback of user '%s' from IP '%s'"
        logger.info(logmsg, client_info.username, client_info.ip, code, reason)

        logger.debug(debug_logmsg, client_info.username, client_info.ip, exc_info=e)
    except Exception:
        logger.exception("Unexpected Exception during WebSocket connection:")
    finally:
        del state.ws_clients[client_id]
