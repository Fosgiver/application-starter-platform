from pwdlib import PasswordHash


password_hasher = PasswordHash.recommended()

DUMMY_PASSWORD_HASH = password_hasher.hash(
    "not-a-real-user-password"
)


def hash_password(plain_password: str) -> str:
    return password_hasher.hash(plain_password)


def verify_password(
    plain_password: str,
    stored_password_hash: str,
) -> bool:
    return password_hasher.verify(
        plain_password,
        stored_password_hash,
    )


def perform_dummy_password_check(
    plain_password: str,
) -> None:
    password_hasher.verify(
        plain_password,
        DUMMY_PASSWORD_HASH,
    )