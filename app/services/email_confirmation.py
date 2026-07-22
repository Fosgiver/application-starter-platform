from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.one_time_tokens import hash_one_time_token
from app.models import (
    AccountToken,
    AccountTokenPurpose,
    User,
)
from app.services.account_tokens import (
    ensure_utc,
    mark_account_token_used,
    utc_now,
)


class InvalidEmailVerificationTokenError(Exception):
    pass


class EmailAlreadyVerifiedError(Exception):
    pass


def confirm_email_verification(
    database_session: Session,
    raw_token: str,
) -> User:
    token_hash = hash_one_time_token(raw_token)

    statement = select(AccountToken).where(
        AccountToken.token_hash == token_hash,
        AccountToken.purpose
        == AccountTokenPurpose.EMAIL_VERIFICATION.value,
    )

    account_token = database_session.scalar(statement)

    if account_token is None:
        raise InvalidEmailVerificationTokenError

    user = database_session.get(
        User,
        account_token.user_id,
    )

    if user is None:
        raise InvalidEmailVerificationTokenError

    if user.is_email_verified:
        raise EmailAlreadyVerifiedError

    if account_token.used_at is not None:
        raise InvalidEmailVerificationTokenError

    if account_token.revoked_at is not None:
        raise InvalidEmailVerificationTokenError

    if ensure_utc(account_token.expires_at) <= utc_now():
        raise InvalidEmailVerificationTokenError

    user.is_email_verified = True
    user.email_verified_at = utc_now()

    mark_account_token_used(account_token)

    database_session.commit()
    database_session.refresh(user)

    return user