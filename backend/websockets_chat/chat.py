from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends, WebSocketException
from authorization import authorize_request_depends
from services.postgres_service import User, get_session_depends, merge_model
from services.core_services.main_services import MainChatService
from services.core_services.core_services import MainServiceContextManager
from websockets_chat.connection_manager import WebsocketConnectionManager

from pydantic_schemas.pydantic_schemas_chat import ChatResponse
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

chat = APIRouter()

connection = WebsocketConnectionManager()

@chat.get("/chat/messages/{room}")
async def get_messages(
    room: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> List[ChatResponse]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return
    

@chat.websocket("/ws/{token}")
async def connect_to_websocket_chat_room(
    websocket: WebSocket,
    token: str,
    session: AsyncSession = Depends(get_session_depends)
):
    await connection.connect()
    try:
        while True:
            data = websocket.receive_json()
            # TODO: Implement main logic
    except WebSocketDisconnect:
        pass
    except Exception as e:
        # TODO: Add logs
        pass
    