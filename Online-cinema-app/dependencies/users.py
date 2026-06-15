from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session_postgresql import get_db
from models.users import UserModel
from security.token import decode_token

oauth2_schema = OAuth2PasswordBearer(tokenUrl="login")


async def get_current_user_model(
    token: str = Depends(oauth2_schema), db: AsyncSession = Depends(get_db)
):
    # return current user model from token
    try:
        user_id = decode_token(token)
    except (ExpiredSignatureError, InvalidTokenError):
        raise HTTPException(status_code=401, detail="Token is invalid or expired")
    user_result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User is not registered")
    return user


async def get_user_by_id(user_id: int, db: AsyncSession) -> UserModel:
    user_result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User is not found")
    return user


async def get_user_by_email(user_email: str, db: AsyncSession) -> UserModel:
    user_result = await db.execute(
        select(UserModel).where(UserModel.email == user_email)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User is not found")
    return user
