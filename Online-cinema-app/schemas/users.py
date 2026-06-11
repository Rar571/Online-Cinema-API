from pydantic import BaseModel
from pydantic.v1 import EmailStr


class UserBaseSchema(BaseModel):
    email: EmailStr


class UserRegistrationSchema(UserBaseSchema):
    password: str
