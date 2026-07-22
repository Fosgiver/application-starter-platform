from app.auth.one_time_tokens import (
    generate_one_time_token,
    hash_one_time_token,
)


def test_one_time_token_generation_and_hashing() -> None:
    first_token = generate_one_time_token()
    second_token = generate_one_time_token()

    first_hash = hash_one_time_token(first_token)

    assert first_token != second_token
    assert first_hash != first_token
    assert len(first_hash) == 64
    assert hash_one_time_token(first_token) == first_hash
    assert hash_one_time_token(second_token) != first_hash