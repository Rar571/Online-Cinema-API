from passlib.context import CryptContext
import re

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=14, deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def check_password_complexity(password: str):
    if len(password) < 8:
        return "Password must contain at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return "Password must have at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must have at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must have at least one digit"
    if not re.search(r"[@$!%*?&#]", password):
        return "Password must contains at least one special character: @, $, !, %, *, ?, &, #."
    return None
