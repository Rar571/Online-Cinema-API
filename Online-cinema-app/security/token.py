import os
import secrets
import jwt
from datetime import datetime, timezone, timedelta

from jwt import ExpiredSignatureError, InvalidTokenError


def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


def generate_access_token(data: dict):
    to_encode = data.copy()
    to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def generate_refresh_token(data: dict):
    to_encode = data.copy()
    to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> int:
    # returns user id or ValueError
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithm=ALGORITHM)
        user_id = int(payload.get("sub"))
        return user_id
    except ExpiredSignatureError:
        raise ValueError("Expired token")
    except InvalidTokenError:
        raise ValueError("Invalid token")
