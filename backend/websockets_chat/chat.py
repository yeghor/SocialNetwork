from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends, Body
from authorization import authorize_request_depends
from services.postgres_service import User, get_session_depends, merge_model
from services.core_services.main_services import MainChatService
from services.core_services.core_services import MainServiceContextManager
from websockets_chat.connection_manager import WebsocketConnectionManager

from exceptions.custom_exceptions import WSInvaliddata
from pydantic_schemas.pydantic_schemas_chat import ChatResponse, CreateDialoqueRoomBody, CreateGroupRoomBody, ExpectedWSData
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

chat = APIRouter()

connection = WebsocketConnectionManager()

@chat.get("/chat/{room_id}")
async def get_messages_and_token(
    room_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> List[ChatResponse]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return

@chat.post("/chat/dialoque")
async def create_dialoque_chat(
    data: CreateDialoqueRoomBody = Body(...),  
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
):
    user = await merge_model(postgres_session=session, model_obj=user_)

@chat.post("chat/group")
async def create_group_chat(
    data: CreateGroupRoomBody,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
):
    user = await merge_model(postgres_session=session, model_obj=user_)


@chat.get("/chat")
async def get_my_chats(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)  
):
    pass

@chat.websocket("/ws/{token}")
async def connect_to_websocket_chat_room(
    websocket: WebSocket,
    token: str,
    session: AsyncSession = Depends(get_session_depends)
):
    await connection.connect()
    while True:
        try:
            data = websocket.receive_json()
            # TODO: Implement main logic
        except WSInvaliddata:
            # todo: Add logs
            pass
            break
        except WebSocketDisconnect:
            break
        except Exception as e:
            # TODO: Add logs
            pass
        break
                
    