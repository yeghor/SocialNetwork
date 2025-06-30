from pydantic import BaseModel, field_validator, ValidationInfo
from datetime import datetime
from typing import Any

class PayloadJWT(BaseModel):
    user_id: str
    issued_at: datetime

    @field_validator("issued_at", mode="after")
    @classmethod
    def from_unix_to_datetime(cls, value: Any) -> datetime:
        if isinstance(value, int):
            value = datetime.fromtimestamp(value)
        return value
