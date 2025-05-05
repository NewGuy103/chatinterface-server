import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect, status

logger: logging.Logger = logging.getLogger("chatinterface_server")


class WebsocketClients:
    def __init__(self):
        self.clients: dict[str, dict[str, list[WebSocket]]] = {}
        self.dropped_clients: list[WebSocket] = []

        self.clean_clients_task = asyncio.ensure_future(self._check_clients_state())

    def add_client(self, username: str, token: str, websocket: WebSocket) -> None:
        if username not in self.clients:
            self.clients[username] = {}
        
        session_dict: dict[str, list[WebSocket]] = self.clients[username]
        if token not in session_dict:
            session_dict[token] = []

        session_dict[token].append(websocket)

    def check_client_disconnected(self, websocket: WebSocket):
        return websocket in self.dropped_clients

    async def _check_clients_state(self):
        while True:
            await asyncio.sleep(0.05)
            for session_dict in self.clients.values():
                for ws_list in session_dict.values():
                    for ws in ws_list:
                        if ws.client_state.name != "DISCONNECTED":
                            continue

                        self.dropped_clients.append(ws)
                        ws_list.remove(ws)

    async def broadcast_message(self, username: str, message_name: str, message_data: dict):
        if username not in self.clients:
            return

        broadcasted_message: dict = {
            'message': message_name,
            'data': message_data
        }
        session_dict = self.clients[username]

        for token, ws_list in session_dict.items():
            for ws in ws_list:
                connecting_host: str = f"{ws.client.host}:{ws.client.port}"
                try:
                    await ws.send_json(broadcasted_message)
                except (RuntimeError, WebSocketDisconnect) as e:  # socket already closed
                    logger.warning(
                        "Could not broadcast message to socket on %s with session token %s",
                        connecting_host, token, exc_info=e
                    )
                    continue
    
    async def disconnect_clients_by_token(
            self, username: str, token: str,
            message_name: str,
            message_data: str
    ):
        if username not in self.clients:
            return

        session_dict = self.clients[username]
        if token not in session_dict:
            return

        for ws in session_dict[token]:
            await self.disconnect_client(username, token, ws, message_name, message_data)

    async def disconnect_all_clients(self, username: str, message_name: str, message_data: str):
        if username not in self.clients:
            return

        session_dict = self.clients[username]
        for token in session_dict.keys():
            await self.disconnect_clients_by_token(username, token, message_name, message_data)

    async def disconnect_client(
            self, username: str, token: str,
            websocket: WebSocket,
            message_name: str,
            message_data: str
    ):
        connecting_host: str = f"{websocket.client.host}:{websocket.client.port}"
        if username not in self.clients:
            return
        
        session_dict = self.clients[username]
        if token not in session_dict:
            return
        
        if websocket not in session_dict[token]:
            logger.debug("Websocket from [%s] not in clients list", connecting_host)
            return

        broadcasted_message: dict = {
            'message': message_name,
            'data': message_data
        }
        try:
            await websocket.send_json(broadcasted_message)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except (RuntimeError, WebSocketDisconnect) as e:
            logger.warning(
                "Could not close websocket on %s", connecting_host,
                exc_info=e
            )
            return
