import asyncio
import uuid
import logging
import msgpack

from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from ..models import (
    Model_SessionInfo, Model_AppState, Model_ChatWSMessageSend,
    Model_WSClientInfo, Model_WSMessageData
)

router: APIRouter = APIRouter(prefix="/ws", tags=['websocket'])
logger: logging.Logger = logging.getLogger("chatinterface.logger.ws")


async def ws_send_msg(ws: WebSocket, message: str, data: dict) -> bytes:
    payload: str = {
        'message': message,
        'data': data
    }
    await ws.send_bytes(msgpack.packb(payload))


@router.websocket("/chat")
async def create_websocket(websocket: WebSocket):
    state: Model_AppState = websocket.state
    await websocket.accept()

    try:
        try:
            auth_msg: bytes = await asyncio.wait_for(websocket.receive_bytes(), timeout=20)
        except KeyError:
            # Starlette's receive_bytes() uses dict['key'] directly, which means
            # if I get a text frame, it ends up as a KeyError
            await websocket.close(code=1003, reason="BINARY_ENDPOINT")
            return

    except asyncio.TimeoutError:
        logger.warning("Waited for client to send authentication data, timed out")
        await websocket.close(code=1008, reason="AUTH_TIMEOUT")
        return
    except WebSocketDisconnect as e:
        code: int = e.code
        reason: str | None = e.reason or None

        logger.info(
            "Client disconnected before sending authentication data [code: %d, reason: %s]",
            code, reason
        )
        return
    except Exception:  # noqa: catch all and return server error
        logger.exception("Unexpected Exception when waiting for authentication data")
        await websocket.close(code=1011, reason="SERVER_ERROR")

        return

    try:
        auth_data: dict = msgpack.unpackb(auth_msg)
    except Exception:
        logger.warning("Client sent invalid MessagePack data during authentication")
        await websocket.close(code=1003, reason="INVALID_MSGPACK")
        return

    # fail with invalid credentials intentionally
    session_token: str = auth_data.get('session_token', '')
    if not session_token or not isinstance(session_token, str):
        await websocket.close(code=1008, reason="INVALID_CREDENTIALS")
        return

    session_valid: bool = await state.db.users.check_session_validity(session_token)
    if not session_valid:
        await websocket.close(code=1008, reason="INVALID_CREDENTIALS")
        return
    
    session_info: Model_SessionInfo = Model_SessionInfo(
        **await state.db.users.get_session_info(session_token)
    )
    client_id: str = str(uuid.uuid4())

    client_info_dict: dict[str, WebSocket | str] = {
        'ws': websocket,
        'ip': f"{websocket.client.host}:{websocket.client.port}",
        'username': session_info.username,
        'token': session_info.token
    }

    client_info: Model_WSClientInfo = Model_WSClientInfo(**client_info_dict)
    state.ws_clients[client_id] = client_info

    await websocket.send_bytes(msgpack.packb("OK"))
    try:
        ws_authorized_logmsg: str = "WebSocket by user '%s' from IP '%s' authorized"
        logger.debug(ws_authorized_logmsg, client_info.username, client_info.ip)

        while True:
            try:
                ws_message: bytes = await websocket.receive_bytes()
            except KeyError:
                # Starlette's receive_bytes() uses dict['key'] directly, which means
                # if I get a text frame, it ends up as a KeyError
                await websocket.close(code=1003, reason="BINARY_ENDPOINT")
                return

            try:
                unpacked_data: dict = msgpack.unpackb(ws_message)
            except Exception as e:
                logger.warning("Client sent invalid MessagePack data as message", exc_info=e)
                await websocket.close(code=1003, reason="INVALID_MSGPACK")
                return

            if not isinstance(unpacked_data, dict):
                await websocket.close(code=1003, reason="INVALID_MSGPACK")
                return

            try:
                loaded_msg: Model_WSMessageData = Model_WSMessageData(**unpacked_data)
            except ValidationError:
                await websocket.close(code=1008, reason="INVALID_DATA")
                return

            match loaded_msg.message:
                case "message.send":
                    await websocket_message_send(websocket, loaded_msg, session_info, state)
                case _:
                    await websocket.close(code=1008, reason="INVALID_MESSAGE")
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


async def websocket_message_send(
        ws: WebSocket, data: Model_WSMessageData,
        session: Model_SessionInfo,
        state: Model_AppState
):
    try:
        msg_data: Model_ChatWSMessageSend = Model_ChatWSMessageSend(**data.data)
    except ValidationError:
        await ws.close(code=1008, reason="message.send INVALID_DATA")
        return

    result: str | int = await state.db.messages.store_message(
        session.username, msg_data.recipient,
        msg_data.data
    )
    match result:
        case 0:
            pass
        case "NO_RECIPIENT":
            return await ws_send_msg(ws, data.message, {'error': result})
        case _:
            logger.error("Unexpected data while storing message: %s", result)
            return await ws.close(code=1011, reason="message.send SERVER_ERROR")

    current_time: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    recipient_payload: dict = {
        'sender': session.username,
        'data': msg_data.data,
        'timestamp': current_time
    }
    for client_info in state.ws_clients.values():
        if client_info.username != msg_data.recipient:
            continue

        recipient_ws: WebSocket = client_info.ws
        await ws_send_msg(recipient_ws, "message.received", recipient_payload)

    success_payload: dict = {
        'id': msg_data.id,
        'recipient': msg_data.recipient,
        'timestamp': current_time
    }
    await ws_send_msg(ws, "message.completed", success_payload)
