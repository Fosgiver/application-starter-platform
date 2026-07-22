from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.one_time_tokens import (
    generate_one_time_token,
    hash_one_time_token,
)
from app.models import AccountToken, AccountTokenPurpose


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def issue_account_token(
    database_session: Session,
    user_id: UUID,
    purpose: AccountTokenPurpose,
    lifetime_minutes: int,
) -> str:
    now = utc_now()

    database_session.execute(
        update(AccountToken)
        .where(
            AccountToken.user_id == user_id,
            AccountToken.purpose == purpose.value,
            AccountToken.used_at.is_(None),
            AccountToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )

    raw_token = generate_one_time_token()

    account_token = AccountToken(
        user_id=user_id,
        purpose=purpose.value,
        token_hash=hash_one_time_token(raw_token),
        expires_at=now + timedelta(minutes=lifetime_minutes),
    )

    database_session.add(account_token)
    database_session.commit()

    return raw_token


def find_valid_account_token(
    database_session: Session,
    raw_token: str,
    purpose: AccountTokenPurpose,
) -> AccountToken | None:
    token_hash = hash_one_time_token(raw_token)

    statement = select(AccountToken).where(
        AccountToken.token_hash == token_hash,
        AccountToken.purpose == purpose.value,
        AccountToken.used_at.is_(None),
        AccountToken.revoked_at.is_(None),
    )

    account_token = database_session.scalar(statement)

    if account_token is None:
        return None

    if ensure_utc(account_token.expires_at) <= utc_now():
        return None

    return account_token


def mark_account_token_used(
    account_token: AccountToken,
) -> None:
    account_token.used_at = utc_now()