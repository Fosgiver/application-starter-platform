from app.auth.passwords import hash_password, verify_password


def test_password_hash_and_verification() -> None:
    plain_password = "StrongTestPassword!123"

    stored_password_hash = hash_password(plain_password)

    assert stored_password_hash != plain_password

    assert verify_password(
        plain_password,
        stored_password_hash,
    )

    assert not verify_password(
        "WrongPassword!123",
        stored_password_hash,
    )