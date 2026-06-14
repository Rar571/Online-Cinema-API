from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session_postgresql import get_db
from models.users import UserModel, UserGroupModel, UserGroupEnum
from security.token import decode_token

oauth2_schema = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user_model(token: str = Depends(oauth2_schema), db: AsyncSession = Depends(get_db)):
    # return current user model from token
    try:
        user_id = decode_token(token)
    except (ExpiredSignatureError, InvalidTokenError):
        raise HTTPException(status_code=401, detail="Token is invalid or expired")
    user_result = await db.execute(select(UserModel).where(
        UserModel.id == user_id
    ))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User is not registered")
    return user


group_moderators_id = None
group_admins_id = None
group_users_id = None


async def get_groups_id(db: AsyncSession = Depends(get_db)):
    global group_moderators_id, group_admins_id, group_users_id
    group_moderators_result = await db.execute(select(UserGroupModel).where(
        UserGroupModel.name == UserGroupEnum.MODERATOR
    ))
    group_moderators = group_moderators_result.scalar_one()
    group_moderators_id = group_moderators.id
    group_admins_result = await db.execute(select(UserGroupModel).where(
        UserGroupModel.name == UserGroupEnum.ADMIN
    ))
    group_admins = group_admins_result.scalar_one()
    group_admins_id = group_admins.id
    group_users_result = await db.execute(select(UserGroupModel).where(
        UserGroupModel.name == UserGroupEnum.USER
    ))
    group_users = group_users_result.scalar_one()
    group_users_id = group_users.id


async def require_moderator(current_user: UserModel = Depends(get_current_user_model)):
    if current_user.group_id == group_admins_id:
        return current_user
    if current_user.group_id != group_moderators_id:
        raise HTTPException(status_code=403, detail="You do not have access to this feature")
    return current_user


async def require_admin(current_user: UserModel = Depends(get_current_user_model)):
    if current_user.group_id != group_admins_id:
        raise HTTPException(status_code=403, detail="You do not have access to this feature")
    return current_user
