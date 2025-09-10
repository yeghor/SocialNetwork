from fastapi.websockets import WebSocket
from pydantic_schemas.pydantic_schemas_chat import ExpectedWSData, ChatJWTPayload, ActionType, MessageSchema, MessageSchemaShort
from typing import List, Dict
import json
from exceptions.custom_exceptions import NoActiveConnectionsOrRoomDoesNotExist

class WebsocketConnectionManager:
    _instance=None
    _isinitialized=False

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_room_connections(self, room_id: str) -> List[Dict]:
        """Returns room connections or raise NoActiveConnectionsOrRoomDoesNotExist exception."""
        possible_conns =  self.rooms.get(room_id)
        if not possible_conns: raise NoActiveConnectionsOrRoomDoesNotExist(
            f"WebSocketConnectionManager: User tried to get room: {room_id} but no active connections found"
            )
        return possible_conns
    
    def __init__(self):
        """
        This manager is only for **fast local** message update between connections.

        It's do **NOT** syncing with PostgreSQL
        """
        if self._isinitialized:
            return
        
        self._isinitialized = True

        self.rooms = {}

    async def execute_real_time_action(self, action: ActionType, connection_data: ChatJWTPayload, db_message_data: MessageSchemaShort | MessageSchema ) -> None:
        if action == "send":
            await self._send_message(db_message_data=db_message_data, room_id=connection_data.room_id, sender_id=connection_data.user_id)
        elif action == "change":
            await self._change_message(db_message_data=db_message_data, room_id=connection_data.room_id, sender_id=connection_data.user_id)
        elif action == "delete":
            await self._delete_message(db_message_data=db_message_data, room_id=connection_data.room_id, sender_id=connection_data.user_id)

    def connect(self, room_id: str, user_id: str, websocket: WebSocket) -> None:
        payload = {
            "user_id": user_id,
            "websocket": websocket
        }

        if not room_id in self.rooms.keys():
            self.rooms[room_id] = [payload]
        else:
            self.rooms[room_id].append(payload)
        print(self.rooms)

    def disconnect(self, room_id: str, websocket: WebSocket) -> None:
        connections = self._get_room_connections(room_id=room_id)

        for conn in connections   :
            if conn["websocket"] == websocket:
                connections.remove(conn)
                return

    async def _send_message(self, db_message_data: MessageSchema, room_id: str, sender_id: str) -> None:
        """Sends message to room and all online room members"""
        connections = self._get_room_connections(room_id=room_id)

        for conn in connections:
            if conn["user_id"] == sender_id:
                continue
            
            websocket: WebSocket = conn["websocket"]
            
            await websocket.send_json(
                db_message_data.model_json_schema()
            )


    async def _delete_message(self, db_message_data: MessageSchemaShort, room_id: str, sender_id: str) -> None:
        connections = self._get_room_connections(room_id=room_id)

        for conn in connections:
            if conn["user_id"] == sender_id:
                continue

            websocket: WebSocket = conn["websocket"]

            await websocket.send_json(
                db_message_data.model_json_schema()
            )

    async def _change_message(self, db_message_data: MessageSchema, room_id: str, sender_id: str) -> None:
        connections = self._get_room_connections(room_id=room_id)
        
        for conn in connections:
            if conn["user_id"] == sender_id:
                continue

            websocket: WebSocket = conn["websocket"]

            await websocket.send_json(
                db_message_data.model_json_schema()
            )