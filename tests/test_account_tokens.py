from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.one_time_tokens import hash_one_time_token
from app.db.database import Base
from app.models import AccountToken, AccountTokenPurpose
from app.services.account_tokens import (
    find_valid_account_token,
    issue_account_token,
    mark_account_token_used,
)
from app.services.accounts import register_user


def create_test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    return engine


def test_account_token_lifecycle() -> None:
    engine = create_test_engine()

    with Session(engine) as database_session:
        user = register_user(
            database_session,
            email="user@example.com",
            plain_password="StrongTestPassword!123",
        )

        raw_token = issue_account_token(
            database_session,
            user_id=user.id,
            purpose=AccountTokenPurpose.EMAIL_VERIFICATION,
            lifetime_minutes=30,
        )

        stored_token = find_valid_account_token(
            database_session,
            raw_token=raw_token,
            purpose=AccountTokenPurpose.EMAIL_VERIFICATION,
        )

        assert stored_token is not None
        assert stored_token.token_hash == hash_one_time_token(raw_token)
        assert stored_token.token_hash != raw_token
        assert stored_token.used_at is None
        assert stored_token.revoked_at is None

        mark_account_token_used(stored_token)
        database_session.commit()

        assert (
            find_valid_account_token(
                database_session,
                raw_token=raw_token,
                purpose=AccountTokenPurpose.EMAIL_VERIFICATION,
            )
            is None
        )


def test_new_token_revokes_previous_token() -> None:
    engine = create_test_engine()

    with Session(engine) as database_session:
        user = register_user(
            database_session,
            email="user@example.com",
            plain_password="StrongTestPassword!123",
        )

        first_token = issue_account_token(
            database_session,
            user_id=user.id,
            purpose=AccountTokenPurpose.EMAIL_VERIFICATION,
            lifetime_minutes=30,
        )

        second_token = issue_account_token(
            database_session,
            user_id=user.id,
            purpose=AccountTokenPurpose.EMAIL_VERIFICATION,
            lifetime_minutes=30,
        )

        assert (
            find_valid_account_token(
                database_session,
                raw_token=first_token,
                purpose=AccountTokenPurpose.EMAIL_VERIFICATION,
            )
            is None
        )

        assert (
            find_valid_account_token(
                database_session,
                raw_token=second_token,
                purpose=AccountTokenPurpose.EMAIL_VERIFICATION,
            )
            is not None
        )

        stored_tokens = database_session.scalars(
            select(AccountToken).where(
                AccountToken.user_id == user.id,
                AccountToken.purpose
                == AccountTokenPurpose.EMAIL_VERIFICATION.value,
            )
        ).all()

        assert len(stored_tokens) == 2

        tokens_by_hash = {
            stored_token.token_hash: stored_token
            for stored_token in stored_tokens
        }

        first_stored_token = tokens_by_hash[
            hash_one_time_token(first_token)
        ]
        second_stored_token = tokens_by_hash[
            hash_one_time_token(second_token)
        ]

        assert first_stored_token.revoked_at is not None
        assert first_stored_token.used_at is None

        assert second_stored_token.revoked_at is None
        assert second_stored_token.used_at is None