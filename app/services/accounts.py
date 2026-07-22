from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password
from app.models import User


class EmailAlreadyRegisteredError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(
    database_session: Session,
    email: str,
) -> User | None:
    normalized_email = normalize_email(email)

    statement = select(User).where(
        User.email == normalized_email,
    )

    return database_session.scalar(statement)


def register_user(
    database_session: Session,
    email: str,
    plain_password: str,
) -> User:
    normalized_email = normalize_email(email)

    if get_user_by_email(database_session, normalized_email) is not None:
        raise EmailAlreadyRegisteredError

    user = User(
        email=normalized_email,
        password_hash=hash_password(plain_password),
    )

    database_session.add(user)

    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        raise EmailAlreadyRegisteredError from error

    database_session.refresh(user)

    return user