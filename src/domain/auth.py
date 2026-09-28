"""Authentication value objects used by the API boundary."""

from pydantic import BaseModel, ConfigDict, Field


class AuthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str = Field(min_length=1)
    token_type: str = "bearer"
    user_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
