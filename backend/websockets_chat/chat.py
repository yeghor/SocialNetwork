from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends, Body
from authorization import authorize_request_depends, authorize_chat_token, JWTService
from services.postgres_service import User, get_session_depends, merge_model
from services.core_services.main_services import MainChatService
from services.core_services.core_services import MainServiceContextManager
from websockets_chat.connection_manager import WebsocketConnectionManager

from exceptions.exceptions_handler import endpoint_exception_handler, ws_endpoint_exception_handler

from pydantic_schemas.pydantic_schemas_chat import *
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from routes.query_utils import page_validator

chat = APIRouter()

connection = WebsocketConnectionManager()

@chat.get("/chat/connect/{chat_id}")
# @endpoint_exception_handler
async def get_chat_token_participants_avatar_urls(
    chat_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> ChatTokenResponse:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return await chat.get_chat_token_participants_avatar_urls(room_id=chat_id, user=user)

@chat.get("/chat/{chat_id}/messages/{page}")
@endpoint_exception_handler
async def get_batch_of_chat_messages(
    chat_id: str,
    page: int = Depends(page_validator),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> List[MessageSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return await chat.get_messages_batch(room_id=chat_id, user=user, page=page)

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

@chat.post("/chat/group")
@endpoint_exception_handler
async def create_group_chat(
    data: CreateGroupRoomBody,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        await chat.create_group_chat(data=data, user=user)

@chat.get("/chat/{page}")
@endpoint_exception_handler
async def get_my_chats(
    page: int = Depends(page_validator),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)  
) -> List[Chat]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return await chat.get_chat_batch(user=user, page=page, chat_type="chat")

@chat.get("/chat/not-approved/{page}")
@endpoint_exception_handler
async def get_not_approved_chats(
    page: int = Depends(page_validator),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)  
) -> List[Chat]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return await chat.get_chat_batch(user=user, page=page, chat_type="not-approved")

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

async def wsconnect(token: str, websocket: WebSocket) -> ChatJWTPayload:
    connection_data = JWTService.extract_chat_jwt_payload(jwt_token=token)
    await connection.connect(room_id=connection_data.room_id, user_id=connection_data.user_id, websocket=websocket)

    await websocket.accept()
    
    return connection_data

@chat.websocket("/ws/{token}")
# @ws_endpoint_exception_handler
async def connect_to_websocket_chat_room(
    websocket: WebSocket,
    token: str = Depends(authorize_chat_token),
    session: AsyncSession = Depends(get_session_depends)
):
    connection_data = await wsconnect(token=token, websocket=websocket)

    try:
        while True:
            json_dict = await websocket.receive_json()

            # If in json_dict enough data - it passes not related fields
            request_data = ExpectedWSData.model_validate(json_dict, strict=True)

            async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
                db_message_data = await chat.execute_action(request_data=request_data, connection_data=connection_data)

            await connection.execute_real_time_action(action=request_data.action, connection_data=connection_data, db_message_data=db_message_data)

    finally:
        await connection.disconnect(room_id=connection_data.room_id, websocket=websocket)
