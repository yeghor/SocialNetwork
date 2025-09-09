from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends, Body
from authorization import authorize_request_depends, JWTService
from services.postgres_service import User, get_session_depends, merge_model
from services.core_services.main_services import MainChatService
from services.core_services.core_services import MainServiceContextManager
from websockets_chat.connection_manager import WebsocketConnectionManager

from exceptions.custom_exceptions import WSInvaliddata, NoActiveConnectionsOrRoomDoesNotExist
from exceptions.exceptions_handler import endpoint_exception_handler, ws_endpoint_exception_handler

from pydantic_schemas.pydantic_schemas_chat import *
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from routes.query_utils import query_exclude_required

chat = APIRouter()

connection = WebsocketConnectionManager()

@chat.get("/chat/connect/{chat_id}")
@endpoint_exception_handler
async def get_chat_token(
    chat_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> ChatTokenResponse:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return await chat.get_chat_token(room_id=chat_id, user=user)

@chat.get("/chat/{chat_id}/messages")
@endpoint_exception_handler
async def get_batch_of_chat_messages(
    chat_id: str,
    exclude: bool = Depends(query_exclude_required),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> List[MessageSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return await chat.get_messages_batch(room_id=chat_id, user=user, exclude=exclude)

@chat.post("/chat/dialoque")
@endpoint_exception_handler
async def create_dialoque_chat(
    data: CreateDialoqueRoomBody = Body(...),  
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return await chat.create_dialogue_chat(data=data, user=user)

@chat.post("chat/group")
@endpoint_exception_handler
async def create_group_chat(
    data: CreateGroupRoomBody,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        await chat.create_group_chat(data=data, user=user)

@chat.get("/chat")
@endpoint_exception_handler
async def get_my_chats(
    exclude: bool = Depends(query_exclude_required),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)  
) -> List[Chat]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return await chat.get_chat_batch(user=user, exclude=exclude, chat_type="chat")

@chat.get("/chat/not-approved")
@endpoint_exception_handler
async def get_not_approved_chats(
    exclude: bool = Depends(query_exclude_required),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)  
) -> List[Chat]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return await chat.get_chat_batch(user=user, exclude=exclude, chat_type="not-approved")

@chat.post("/chat/{chat_id}")
@endpoint_exception_handler
async def approve_chat(
    chat_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return await chat.approve_chat(room_id=chat_id, user=user)

@chat.websocket("/ws/{token}")
# @ws_endpoint_exception_handler
async def connect_to_websocket_chat_room(
    websocket: WebSocket,
    token: str,
    session: AsyncSession = Depends(get_session_depends)
):
    connection_data = JWTService.extract_chat_jwt_payload(jwt_token=token)
    print(connection_data.room_id)
    print(connection_data.user_id)
    connection.connect(room_id=connection_data.room_id, user_id=connection_data.user_id, websocket=websocket)
    await websocket.accept()
    while True:
        json_dict = await websocket.receive_json()
        request_data = ExpectedWSData(**json_dict)

        # await connection.execute_real_time_action(request_data=request_data, connection_data=connection_data)

        # async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        #     await chat.execute_action(request_data=request_data, connection_data=connection_data)
