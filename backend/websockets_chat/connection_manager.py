from fastapi.websockets import WebSocket
from pydantic_schemas.pydantic_schemas_chat import ExpectedWSData, ChatJWTPayload
from typing import List, Dict
import json

class WebsocketConnectionManager:
    # TODO: Add Singleton pattern

    def _get_room_connections(self, room_id: str) -> List[Dict]:
        return self.rooms[room_id]
    
    def __init__(self):
        """
        This manager is only for **fast local** message update between connections.

        It's **NOT** syncing with PostgreSQL
        """
        self.rooms = {}

    async def execute_user_response(self, user_data: ExpectedWSData, connection_data: ChatJWTPayload):
        if user_data.action == "send":
            await self._send_message(message=user_data.message, room_id=connection_data.room_id)
        elif user_data.action == "change":
            await self._change_message(message_id=user_data.message_id, room_id=connection_data.room_id)
        elif user_data.action == "delete":
            await self._delete_message(message_id=user_data.message_id, room_id=connection_data.room_id)

    def connect(self, room_id: str, user_id: str, websocket: WebSocket):
        payload = {
            "user_id": user_id,
            "websocket": websocket
        }
        if not room_id in self.rooms.keys():
            self.rooms[room_id] = [payload]
        else:
            self.rooms[room_id].append(payload)

    def disconnect(self, room_id: str, websocket: WebSocket):
        connections = self._get_room_connections(room_id=room_id)
        for conn in connections   :
            if conn["websocket"] == websocket:
                connections.remove(conn)
                return

    async def _send_message(self, message: str, room_id: str):
        """Sends message to room and all online room members"""
        connections = self._get_room_connections(room_id=room_id)
        for conn in connections:
            websocket: WebSocket = conn["websocket"]
            
            await websocket.send_json(
                {
                    "action": "send",
                    "user_id": conn["user_id"],
                    "message": message
                }
            )


    async def _delete_message(self, message_id: str, room_id: str):
        connections = self._get_room_connections(room_id=room_id)

        for conn in connections:
            websocket: WebSocket = conn["websocket"]

            await websocket.send_json(
                {
                    "action": "delete",
                    "message_id": message_id
                }
            )

    async def _change_message(self, message_id: str, room_id: str, new_message: str):
        connections = self._get_room_connections(room_id=room_id)
        
        for conn in connections:
            websocket: WebSocket = conn["websocket"]

            await websocket.send_json(
                {
                    "action": "change",
                    "message_id": message_id,
                    "message": new_message
                }
            )