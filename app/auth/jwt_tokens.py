from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from jwt.exceptions import InvalidTokenError

from app.core.settings import settings


class InvalidAccessTokenError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def access_token_lifetime_seconds() -> int:
    return settings.jwt_access_token_minutes * 60


def create_access_token(
    user_id: UUID,
    expires_delta: timedelta | None = None,
) -> str:
    issued_at = utc_now()

    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.jwt_access_token_minutes
        )

    expires_at = issued_at + expires_delta

    payload = {
        "sub": str(user_id),
        "type": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
        "jti": str(uuid4()),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(encoded_token: str) -> UUID:
    try:
        payload = jwt.decode(
            encoded_token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={
                "require": [
                    "sub",
                    "type",
                    "iss",
                    "aud",
                    "iat",
                    "nbf",
                    "exp",
                    "jti",
                ]
            },
        )

        if payload["type"] != "access":
            raise InvalidAccessTokenError

        return UUID(payload["sub"])

    except (
        InvalidTokenError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise InvalidAccessTokenError from error