from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends, Body
from authorization import authorize_request_depends, JWTService
from services.postgres_service import User, get_session_depends, merge_model
from services.core_services.main_services import MainChatService
from services.core_services.core_services import MainServiceContextManager
from websockets_chat.connection_manager import WebsocketConnectionManager

from exceptions.custom_exceptions import WSInvaliddata, NoActiveConnectionsOrRoomDoesNotExist
from exceptions.exceptions_handler import endpoint_exception_handler

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
) -> List[ChatTokenResponse]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return await chat.get_chat_token(room_id=chat_id, user=user)

@chat.get("/chat/{chat_id}/messages")
@endpoint_exception_handler
async def get_batch_chat_messages(
    chat_id: str,
    exclude: bool = Depends(query_exclude_required),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> List[HistoryMessage]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainChatService].create(MainServiceType=MainChatService, postgres_session=session) as chat:
        return await chat.get_chat_messages(room_id=chat_id, user=user)

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


@chat.get("/chat")
@endpoint_exception_handler
async def get_my_chats(
    exclude: bool = Depends(query_exclude_required),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)  
):
    pass

@chat.get("/chat/not-approved")
@endpoint_exception_handler
async def get_not_approved_chats(
    exclude: bool = Depends(query_exclude_required),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)  
) -> List[Chat]:
    pass

@chat.websocket("/ws/{token}")
async def connect_to_websocket_chat_room(
    websocket: WebSocket,
    token: str,
    session: AsyncSession = Depends(get_session_depends)
):
    connection_data = JWTService.extract_chat_jwt_payload(jwt_token=token)
    await connection.connect(websocket)
    while True:
        try:
            user_data: ExpectedWSData = await websocket.receive_json()
            await connection.execute_user_response(user_data=user_data, connection_data=connection_data)
        except WSInvaliddata as e:
            # TODO: Add logs
            pass
            break
        except WebSocketDisconnect:
            break
        except NoActiveConnectionsOrRoomDoesNotExist as e:
            # TODO: Add logs
            pass
        except Exception as e:
            # TODO: Add logs
            pass
        finally:
            await websocket.close()
            break                
    