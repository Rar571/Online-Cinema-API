import re

from pydantic import BaseModel, field_validator
from pydantic.v1 import EmailStr


class UserBaseSchema(BaseModel):
    email: EmailStr


class UserRegistrationSchema(UserBaseSchema):
    password: str

    @field_validator("password")
    @staticmethod
    def validate_password(password: str):
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters.")
        if not re.search(r'[A-Z]', password):
            raise ValueError("Password must have at least one uppercase letter")
        if not re.search(r'[a-z]', password):
            raise ValueError("Password must have at least one lowercase letter")
        if not re.search(r'\d', password):
            raise ValueError("Password must have at least one digit")
        if not re.search(r'[@$!%*?&#]', password):
            raise ValueError("Password must contains at least one special character: @, $, !, %, *, ?, &, #.")
        return password


class UserActivationSchema(UserBaseSchema):
    token: str
