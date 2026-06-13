from pydantic import BaseModel, field_validator, EmailStr

from security.passwords import check_password_complexity


class UserBaseSchema(BaseModel):
    email: EmailStr


class UserRegistrationSchema(UserBaseSchema):
    password: str

    @field_validator("password")
    @staticmethod
    def validate_password(password: str):
        error_message = check_password_complexity(password)
        if error_message:
            raise ValueError(error_message)
        return password


class UserActivationSchema(UserBaseSchema):
    token: str


class UserLoginSchema(UserRegistrationSchema):
    pass


class UserChangePasswordSchema(BaseModel):
    old_password: str

    @field_validator("old_password")
    @staticmethod
    def validate_password(password: str):
        error_message = check_password_complexity(password)
        if error_message:
            raise ValueError(error_message)
        return password

    new_password: str

    @field_validator("new_password")
    @staticmethod
    def validate_password(password: str):
        error_message = check_password_complexity(password)
        if error_message:
            raise ValueError(error_message)
        return password


class UserResetPasswordRequestSchema(UserBaseSchema):
    pass


class UserResetPasswordCompleteSchema(UserBaseSchema):
    new_password: str

    @field_validator("new_password")
    @staticmethod
    def validate_password(password: str):
        error_message = check_password_complexity(password)
        if error_message:
            raise ValueError(error_message)
        return password

    token: str


class UserRefreshAccessTokenSchema(BaseModel):
    refresh_token: str
