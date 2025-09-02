from pydantic import BaseModel, Field, model_validator
from typing import List, Literal
from typing_extensions import Self
from datetime import datetime
from pydantic_schemas.pydantic_schemas_social import UserShortSchemaAvatarURL
from exceptions.custom_exceptions import WSInvaliddata

class HistoryMessage(BaseModel):
    message_id: str
    message: str
    date: datetime = Field(default=datetime.utcnow())
    owner: UserShortSchemaAvatarURL

class ChatResponse(BaseModel):
    messages: List[HistoryMessage]
    token: str

class CreateDialoqueRoomBody(BaseModel):
    user_id: str
    message: str

class CreateGroupRoomBody(BaseModel):
    user_id: str
    message: str

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