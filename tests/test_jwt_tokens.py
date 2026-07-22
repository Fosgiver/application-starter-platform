from datetime import timedelta
from uuid import uuid4

import pytest

from app.auth.jwt_tokens import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
)


def test_access_token_creation_and_decoding() -> None:
    user_id = uuid4()

    encoded_token = create_access_token(user_id)

    decoded_user_id = decode_access_token(encoded_token)

    assert decoded_user_id == user_id


def test_modified_access_token_is_rejected() -> None:
    encoded_token = create_access_token(uuid4())

    modified_token = encoded_token + "modified"

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(modified_token)


def test_expired_access_token_is_rejected() -> None:
    expired_token = create_access_token(
        uuid4(),
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(expired_token)