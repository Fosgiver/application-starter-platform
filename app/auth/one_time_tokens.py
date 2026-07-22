from hashlib import sha256
from secrets import token_urlsafe


def generate_one_time_token() -> str:
    return token_urlsafe(32)


def hash_one_time_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()