from sqlalchemy.orm import Session

from app.auth.passwords import hash_password
from app.models import (
    AccountTokenPurpose,
    User,
)
from app.services.account_tokens import (
    find_valid_account_token,
    mark_account_token_used,
    utc_now,
)


class InvalidPasswordResetTokenError(Exception):
    pass


def complete_password_reset(
    database_session: Session,
    raw_token: str,
    new_password: str,
) -> User:
    account_token = find_valid_account_token(
        database_session,
        raw_token=raw_token,
        purpose=AccountTokenPurpose.PASSWORD_RESET,
    )

    if account_token is None:
        raise InvalidPasswordResetTokenError

    user = database_session.get(
        User,
        account_token.user_id,
    )

    if user is None:
        raise InvalidPasswordResetTokenError

    if not user.is_active:
        raise InvalidPasswordResetTokenError

    user.password_hash = hash_password(new_password)

    if not user.is_email_verified:
        user.is_email_verified = True
        user.email_verified_at = utc_now()

    mark_account_token_used(account_token)

    database_session.commit()
    database_session.refresh(user)

    return user