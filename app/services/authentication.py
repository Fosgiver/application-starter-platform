from sqlalchemy.orm import Session

from app.auth.passwords import (
    perform_dummy_password_check,
    verify_password,
)
from app.models import User
from app.services.accounts import get_user_by_email


class InvalidCredentialsError(Exception):
    pass


class LoginNotPermittedError(Exception):
    pass


class EmailVerificationRequiredError(Exception):
    def __init__(self, user: User) -> None:
        self.user = user
        super().__init__()


def authenticate_user(
    database_session: Session,
    email: str,
    plain_password: str,
) -> User:
    user = get_user_by_email(
        database_session,
        email,
    )

    if user is None:
        perform_dummy_password_check(plain_password)
        raise InvalidCredentialsError

    if not verify_password(
        plain_password,
        user.password_hash,
    ):
        raise InvalidCredentialsError

    if not user.is_active:
        raise LoginNotPermittedError

    if not user.is_email_verified:
        raise EmailVerificationRequiredError(user)

   
    return user