from typing import Annotated

from fastapi import Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session

from app.auth.jwt_tokens import (
    InvalidAccessTokenError,
    decode_access_token,
)
from app.db.database import get_db
from app.models import User


class AuthenticationRequiredError(Exception):
    pass


bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    scheme_name="bearerAuth",
    description=(
        "Short-lived JWT access token returned by login."
    ),
    auto_error=False,
)


BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


def get_current_user(
    credentials: BearerCredentials,
    database_session: DatabaseSession,
) -> User:
    if credentials is None:
        raise AuthenticationRequiredError

    try:
        user_id = decode_access_token(
            credentials.credentials
        )
    except InvalidAccessTokenError as error:
        raise AuthenticationRequiredError from error

    user = database_session.get(
        User,
        user_id,
    )

    if user is None:
        raise AuthenticationRequiredError

    if not user.is_active:
        raise AuthenticationRequiredError

    if not user.is_email_verified:
        raise AuthenticationRequiredError

   
    return user


CurrentUser = Annotated[
    User,
    Depends(get_current_user),
]