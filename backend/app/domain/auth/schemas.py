from pydantic import BaseModel


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str


class RefreshRequest(BaseModel):
    refreshToken: str
