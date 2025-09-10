from pydantic import BaseModel, Field, model_validator, field_validator
from typing import List, Literal, Any
from typing_extensions import Self
from datetime import datetime
from pydantic_schemas.pydantic_schemas_social import UserShortSchema
from exceptions.custom_exceptions import WSInvalidData
from services.postgres_service import User

ActionType = Literal["send", "change", "delete"]

class Chat(BaseModel):
    chat_id: str
    participants: int

class MessageSchemaShort(BaseModel):
    message_id: str

class MessageSchema(MessageSchemaShort):
    text: str
    sent: datetime = Field(default=datetime.utcnow)
    owner: UserShortSchema

class ChatTokenResponse(BaseModel):
    token: str

class CreateChatBodyBase(BaseModel):
    message: str

class CreateDialoqueRoomBody(CreateChatBodyBase):
    other_participant_id: str

class CreateGroupRoomBody(CreateChatBodyBase):
    other_participants_ids: List[str]

class ExpectedWSData(BaseModel):
    action: ActionType

    message: str | None
    message_id: str | None

    @model_validator(mode="after")
    def validate_fields(self) -> Self:
        if self.action == "change":
            if not self.message or not self.message_id:
                raise WSInvalidData(f"Pydantic ExpectedWSData: The Schema received invalid data. Action - {self.action}. Message or it's id missing.")
        elif self.action == "delete":
            if not self.message_id:
                raise WSInvalidData("Pydantic ExpectedWSData: ExpectedWSData schema received invalid data.")
        else:
            if not self.message:
                raise WSInvalidData(f"Pydantic ExpectedWSData: The Schema received invalid data. Action - {self.action}. Message missing.")

        return self
    
class ChatJWTPayload(BaseModel):
    room_id: str
    user_id: str