from pydantic import BaseModel, EmailStr, Field

from src.schemas.organization import OrgResponse
from src.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    org_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=2, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    user: UserResponse
    organization: OrgResponse
    access_token: str
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class TokenPayload(BaseModel):
    sub: str  # user_id
    org_id: str
    role: str
    email: str
    iat: int | None = None
    exp: int | None = None


class BetaSignupRequest(BaseModel):
    email: EmailStr
    source: str | None = Field(default="landing", max_length=50)


class BetaSignupResponse(BaseModel):
    message: str = "Thanks for signing up! We'll be in touch."
