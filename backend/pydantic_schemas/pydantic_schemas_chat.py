from pydantic import BaseModel, Field, model_validator
from typing import List, Literal
from typing_extensions import Self
from datetime import datetime
from pydantic_schemas.pydantic_schemas_social import UserShortSchemaAvatarURL
from exceptions.custom_exceptions import WSInvaliddata

class Chat(BaseModel):
    chat_id: str
    participants: int

class HistoryMessage(BaseModel):
    message_id: str
    message: str
    date: datetime = Field(default=datetime.utcnow)
    owner: UserShortSchemaAvatarURL

class ChatTokenResponse(BaseModel):
    token: str

class CreateChatBodyBase(BaseModel):
    message: str

class CreateDialoqueRoomBody(CreateChatBodyBase):
    other_participant_id: str

class CreateGroupRoomBody(CreateChatBodyBase):
    other_participants_ids: List[str]

class ExpectedWSData(BaseModel):
    action: Literal["send", "change", "delete"]

    message: str | None
    message_id: str | None

    @model_validator(mode="after")
    def validate_fields(self) -> Self:
        if self.action == "change":
            if not self.message or not self.message_id:
                raise WSInvaliddata(f"Pydantic ExpectedWSData: The Schema received invalid data. Action - {self.action}. Message or it's id missing.")
        elif self.action == "delete":
            if not self.message_id:
                raise WSInvaliddata("Pydantic ExpectedWSData: ExpectedWSData schema received invalid data.")
        else:
            if not self.message:
                raise WSInvaliddata(f"Pydantic ExpectedWSData: The Schema received invalid data. Action - {self.action}. Message missing.")
            
class ChatJWTPayload(BaseModel):
    room_id: str
    user_id: str