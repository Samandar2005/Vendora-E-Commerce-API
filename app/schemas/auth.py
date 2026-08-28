from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(from_attributes=True)



class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., alias="refresh")

    model_config = ConfigDict(populate_by_name=True)


class TokenPayload(BaseModel):
    sub: str
    exp: int
    typ: str | None = None