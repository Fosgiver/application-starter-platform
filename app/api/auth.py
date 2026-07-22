import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.auth.jwt_tokens import (
    access_token_lifetime_seconds,
    create_access_token,
)
from app.core.settings import settings
from app.db.database import get_db
from app.schemas import (
    AccountSummary,
    CurrentAccountResponse,
    EmailVerificationRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RegistrationRequest,
    ResetPasswordRequest,
    SimpleResponse,
)
from app.services.accounts import (
    EmailAlreadyRegisteredError,
    get_user_by_email,
    register_user,
)
from app.services.authentication import (
    EmailVerificationRequiredError,
    InvalidCredentialsError,
    LoginNotPermittedError,
    authenticate_user,
)
from app.services.email_confirmation import (
    EmailAlreadyVerifiedError,
    InvalidEmailVerificationTokenError,
    confirm_email_verification,
)
from app.services.email_sender import EmailDeliveryError
from app.services.email_verification import (
    send_email_verification,
)
from app.services.password_reset import (
    send_password_reset,
)
from app.services.password_reset_completion import (
    InvalidPasswordResetTokenError,
    complete_password_reset,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])

DatabaseSession = Annotated[Session, Depends(get_db)]


def error_response(
    status_code: int,
    message: str,
) -> JSONResponse:
    response = SimpleResponse(
        success=False,
        message=message,
    )

    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(),
    )


@router.post(
    "/register",
    response_model=SimpleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
    operation_id="registerUser",
    responses={
        403: {"model": SimpleResponse},
        409: {"model": SimpleResponse},
        503: {"model": SimpleResponse},
    },
)
def register_account(
    request: RegistrationRequest,
    database_session: DatabaseSession,
) -> SimpleResponse | JSONResponse:
    if not settings.self_registration_enabled:
        return error_response(
            status.HTTP_403_FORBIDDEN,
            "Self-registration is not available.",
        )

    try:
        user = register_user(
            database_session,
            email=str(request.email),
            plain_password=request.password,
        )
    except EmailAlreadyRegisteredError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "Email address is already registered.",
        )

    try:
        send_email_verification(
            database_session,
            user,
        )
    except EmailDeliveryError:
        logger.exception(
            "Verification email delivery failed for user_id=%s",
            user.id,
        )

        return error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            (
                "User account was created, but the verification "
                "email could not be sent. Please sign in to "
                "request a new verification email."
            ),
        )

    return SimpleResponse(
        success=True,
        message=(
            "User account created. "
            "Please check your email to verify your account."
        ),
    )


@router.post(
    "/email-verification/confirm",
    response_model=SimpleResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm user email verification",
    operation_id="confirmEmailVerification",
    responses={
        400: {"model": SimpleResponse},
        409: {"model": SimpleResponse},
    },
)
def confirm_email(
    request: EmailVerificationRequest,
    database_session: DatabaseSession,
) -> SimpleResponse | JSONResponse:
    try:
        confirm_email_verification(
            database_session,
            raw_token=request.token,
        )
    except InvalidEmailVerificationTokenError:
        return error_response(
            status.HTTP_400_BAD_REQUEST,
            "Verification token is invalid or expired.",
        )
    except EmailAlreadyVerifiedError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "Email address is already verified.",
        )

    return SimpleResponse(
        success=True,
        message="Email address verified successfully.",
    )


@router.post(
    "/password/forgot",
    response_model=SimpleResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request password reset instructions",
    operation_id="requestPasswordReset",
)
def forgot_password(
    request: ForgotPasswordRequest,
    database_session: DatabaseSession,
) -> SimpleResponse:
    user = get_user_by_email(
        database_session,
        email=str(request.email),
    )

    if user is not None and user.is_active:
        try:
            send_password_reset(
                database_session,
                user,
            )
        except EmailDeliveryError:
            logger.exception(
                "Password reset email delivery failed "
                "for user_id=%s",
                user.id,
            )

    return SimpleResponse(
        success=True,
        message=(
            "If the account can continue, "
            "the appropriate instructions will be sent."
        ),
    )


@router.post(
    "/password/reset",
    response_model=SimpleResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete a password reset",
    operation_id="resetPassword",
    responses={
        400: {"model": SimpleResponse},
    },
)
def reset_password(
    request: ResetPasswordRequest,
    database_session: DatabaseSession,
) -> SimpleResponse | JSONResponse:
    try:
        complete_password_reset(
            database_session,
            raw_token=request.token,
            new_password=request.new_password,
        )
    except InvalidPasswordResetTokenError:
        return error_response(
            status.HTTP_400_BAD_REQUEST,
            "Password reset token is invalid or expired.",
        )

    return SimpleResponse(
        success=True,
        message="Password reset completed successfully.",
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user account",
    operation_id="loginUser",
    responses={
        401: {"model": SimpleResponse},
        403: {"model": SimpleResponse},
        503: {"model": SimpleResponse},
    },
)
def login(
    request: LoginRequest,
    database_session: DatabaseSession,
) -> LoginResponse | JSONResponse:
    try:
        user = authenticate_user(
            database_session,
            email=str(request.email),
            plain_password=request.password,
        )

    except InvalidCredentialsError:
        return error_response(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email address or password.",
        )

    except EmailVerificationRequiredError as error:
        try:
            send_email_verification(
                database_session,
                error.user,
            )
        except EmailDeliveryError:
            logger.exception(
                "Verification email delivery failed for user_id=%s",
                error.user.id,
            )

            return error_response(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                (
                    "Email verification is required, but a new "
                    "verification email could not be sent. "
                    "Please try again later."
                ),
            )

        return error_response(
            status.HTTP_403_FORBIDDEN,
            (
                "Email verification is required. "
                "A new verification email has been sent."
            ),
        )

    except LoginNotPermittedError:
        return error_response(
            status.HTTP_403_FORBIDDEN,
            "Login could not be completed.",
        )

    access_token = create_access_token(user.id)

    return LoginResponse(
        success=True,
        access_token=access_token,
        token_type="bearer",
        expires_in=access_token_lifetime_seconds(),
    )


@router.get(
    "/auth/me",
    response_model=CurrentAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the authenticated user account",
    operation_id="getCurrentAccount",
    responses={
        401: {"model": SimpleResponse},
    },
)
def get_current_account(
    current_user: CurrentUser,
) -> CurrentAccountResponse:
    account_summary = AccountSummary.model_validate(
        current_user
    )

    return CurrentAccountResponse(
        success=True,
        account=account_summary,
    )