from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.settings import settings


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(
        max_length=254,
    )

    password: str = Field(
        min_length=settings.password_min_length,
        max_length=settings.password_max_length,
    )


class EmailVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(
        min_length=1,
    )


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(
        max_length=254,
    )

    password: str = Field(
        min_length=settings.password_min_length,
        max_length=settings.password_max_length,
    )


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(
        max_length=254,
    )


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(
        min_length=1,
    )

    new_password: str = Field(
        min_length=settings.password_min_length,
        max_length=settings.password_max_length,
    )


class AccountSummary(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    account_id: UUID = Field(
        validation_alias="id",
    )

    email: EmailStr

    email_verified: bool = Field(
        validation_alias="is_email_verified",
    )

    created_at: datetime


class CurrentAccountResponse(BaseModel):
    success: bool
    account: AccountSummary


class SimpleResponse(BaseModel):
    success: bool
    message: str


class LoginResponse(BaseModel):
    success: bool
    access_token: str
    token_type: Literal["bearer"] = "bearer"

    expires_in: int = Field(
        gt=0,
    )