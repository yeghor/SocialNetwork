from fastapi.websockets import WebSocket
from pydantic_schemas.pydantic_schemas_chat import ExpectedWSData, ChatJWTPayload, ActionType, MessageSchema, MessageSchemaShort
from typing import List, Dict, Literal
import json
from exceptions.custom_exceptions import NoActiveConnectionsOrRoomDoesNotExist

from services.redis_service import RedisService

from dotenv import load_dotenv
from os import getenv

load_dotenv()

class WebsocketConnectionManager:
    _instance=None
    _isinitialized=False

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_room_connections(self, room_id: str) -> List[Dict]:
        """Returns room connections or raise NoActiveConnectionsOrRoomDoesNotExist exception."""
        possible_conns =  self._rooms.get(room_id)
        if not possible_conns: raise NoActiveConnectionsOrRoomDoesNotExist(
            f"WebSocketConnectionManager: User tried to get room: {room_id} but no active connections found"
            )
        return possible_conns
    
    def __init__(self, mode: Literal["prod", "test"] = "prod"):
        """
        This manager is only for **fast local** message update between connections.

        It's do **NOT** syncing with PostgreSQL

        Switch to mode='test' to connect to test Redis pool
        """
        self._redis: RedisService = RedisService(db_pool=mode)

        if self._isinitialized:
            return
        self._isinitialized = True

        self._rooms = {}


    async def execute_real_time_action(self, action: ActionType, connection_data: ChatJWTPayload, db_message_data: MessageSchemaShort | MessageSchema ) -> None:
        if action == "send":
            await self._send_message(db_message_data=db_message_data, room_id=connection_data.room_id, sender_id=connection_data.user_id)
        elif action == "change":
            await self._change_message(db_message_data=db_message_data, room_id=connection_data.room_id, sender_id=connection_data.user_id)
        elif action == "delete":
            await self._delete_message(db_message_data=db_message_data, room_id=connection_data.room_id, sender_id=connection_data.user_id)

    async def connect(self, room_id: str, user_id: str, websocket: WebSocket) -> None:
        payload = {
            "user_id": user_id,
            "websocket": websocket
        }

        if not room_id in self._rooms.keys():
            self._rooms[room_id] = [payload]
        else:
            self._rooms[room_id].append(payload)

        print(self._rooms)

        await self._redis.connect_user_to_chat(user_id=user_id, room_id=room_id)



    async def disconnect(self, room_id: str, websocket: WebSocket) -> None:
        connections = self._get_room_connections(room_id=room_id)

        for conn in connections   :
            if conn["websocket"] == websocket:
                connections.remove(conn)
                return
        
        await self._redis.disconect_from_chat(room_id=room_id, user_id=connections[room_id]["user_id"])


    async def _send_message(self, db_message_data: MessageSchema, room_id: str, sender_id: str) -> None:
        """Sends message to room and all online room members"""
        connections = self._get_room_connections(room_id=room_id)

        for conn in connections:
            if conn["user_id"] == sender_id:
                continue

            websocket: WebSocket = conn["websocket"]
            
            await websocket.send_json(
                db_message_data.model_dump_json()
            )


    async def _delete_message(self, db_message_data: MessageSchemaShort, room_id: str, sender_id: str) -> None:
        connections = self._get_room_connections(room_id=room_id)

        for conn in connections:
            if conn["user_id"] == sender_id:
                continue

            websocket: WebSocket = conn["websocket"]

            await websocket.send_json(
                db_message_data.model_dump_json()
            )

    async def _change_message(self, db_message_data: MessageSchema, room_id: str, sender_id: str) -> None:
        connections = self._get_room_connections(room_id=room_id)
        
        for conn in connections:
            if conn["user_id"] == sender_id:
                continue

            websocket: WebSocket = conn["websocket"]

            await websocket.send_json(
                db_message_data.model_dump_json()
            )